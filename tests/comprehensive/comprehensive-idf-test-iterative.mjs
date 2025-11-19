#!/usr/bin/env node
/**
 * Comprehensive IDF Creator Test - Iterative Optimization with Progress Tracking
 * Tracks iterations, saves progress, and reverts to best iteration when warnings increase
 */

import { readFileSync, writeFileSync, mkdirSync, existsSync, readdirSync } from 'fs';
import { join, basename } from 'path';
import { exec } from 'child_process';
import { promisify } from 'util';

const execAsync = promisify(exec);

const IDF_CREATOR_API_URL = process.env.IDF_CREATOR_API_URL || 'https://web-production-3092c.up.railway.app';
const ENERGYPLUS_EXE = '/usr/local/bin/energyplus';
const ENERGYPLUS_IDD = '/usr/local/bin/Energy+.idd';
const VAV_MIN_FLOW_SCHEDULE_NAME = 'VAV Minimum Flow Fraction Schedule';
const DEFAULT_VAV_DESIGN_FRACTION = 0.68;
let dynamicVavDesignFraction = null;

// Progress tracking
const PROGRESS_FILE = join(process.cwd(), 'test_progress.json');
const ITERATIONS_DIR = join(process.cwd(), 'test_iterations');

// Ensure iterations directory exists
mkdirSync(ITERATIONS_DIR, { recursive: true });

const WEATHER_FILES = [
  'EnergyPlus-MCP/energyplus-mcp-server/sample_files/USA_CA_San.Francisco.Intl.AP.724940_TMY3.epw',
  'EnergyPlus-MCP/energyplus-mcp-server/illustrative examples/USA_IL_Chicago-OHare.Intl.AP.725300_TMY3.epw'
];

const SAN_FRANCISCO_TEST_ADDRESSES = [
  '1 Dr Carlton B Goodlett Pl, San Francisco, CA 94102',
  '1355 Market St, San Francisco, CA 94103',
  '1 Ferry Building, San Francisco, CA 94111',
  '50 Beale St, San Francisco, CA 94105',
  '375 Beale St, San Francisco, CA 94105'
];

const WEATHER_ADDRESS_MAP = {
  'USA_CA_San.Francisco.Intl.AP.724940_TMY3.epw': SAN_FRANCISCO_TEST_ADDRESSES,
  'usa_ca_san.francisco.intl.ap.724940_tmy3.epw': SAN_FRANCISCO_TEST_ADDRESSES
};

// Current target warning type (for focused optimization)
let currentTargetWarning = null;

// Load progress from previous runs
function loadProgress() {
  if (existsSync(PROGRESS_FILE)) {
    try {
      const content = readFileSync(PROGRESS_FILE, 'utf-8');
      return JSON.parse(content);
    } catch (error) {
      console.warn(`⚠️  Could not load progress file: ${error.message}`);
      return { iterations: [], best_iteration: null };
    }
  }
  return { iterations: [], best_iteration: null };
}

// Save progress
function saveProgress(progress) {
  writeFileSync(PROGRESS_FILE, JSON.stringify(progress, null, 2), 'utf-8');
}

// Get current git commit hash
async function getCurrentGitCommit() {
  try {
    const { stdout } = await execAsync('git rev-parse HEAD', { cwd: process.env.IDF_CREATOR_DIR || '/Users/giovanniamenta/IDF - CREATOR 2/idf-creator' });
    return stdout.trim();
  } catch (error) {
    return 'unknown';
  }
}

// Get current git branch
async function getCurrentGitBranch() {
  try {
    const { stdout } = await execAsync('git rev-parse --abbrev-ref HEAD', { cwd: process.env.IDF_CREATOR_DIR || '/Users/giovanniamenta/IDF - CREATOR 2/idf-creator' });
    return stdout.trim();
  } catch (error) {
    return 'unknown';
  }
}

// Calculate total warning count from test results
// If currentTargetWarning is set, only count warnings matching that type
function calculateTotalWarnings(results) {
  if (!currentTargetWarning) {
    // Count all warnings if no target is set
    return results.reduce((total, result) => {
      if (result.success) {
        return total + (result.warnings?.length || 0);
      }
      return total;
    }, 0);
  }
  
  // Count only warnings matching the target type
  return results.reduce((total, result) => {
    if (result.success && result.warnings) {
      const matchingWarnings = result.warnings.filter(w => 
        w.toLowerCase().includes(currentTargetWarning.toLowerCase())
      );
      return total + matchingWarnings.length;
    }
    return total;
  }, 0);
}

// Find the most frequent warning type to target next
function findNextTargetWarning(progress) {
  if (!progress.iterations || progress.iterations.length === 0) {
    return null;
  }
  
  // Get the latest iteration
  const latest = progress.iterations[progress.iterations.length - 1];
  if (!latest.results || latest.results.length === 0) {
    return null;
  }
  
  // Collect all warnings from successful tests
  const allWarnings = [];
  latest.results.forEach(result => {
    if (result.success) {
      // Try warning_summary first, fallback to warnings array
      if (result.warning_summary && Array.isArray(result.warning_summary)) {
        result.warning_summary.forEach(({ message, count }) => {
          for (let i = 0; i < count; i++) {
            allWarnings.push(message);
          }
        });
      } else if (result.warnings && Array.isArray(result.warnings)) {
        // Fallback: use warnings array directly
        allWarnings.push(...result.warnings);
      }
    }
  });
  
  if (allWarnings.length === 0) {
    return null;
  }
  
  // Count warnings by type (first 60 chars as key)
  const warningCounts = {};
  allWarnings.forEach(w => {
    const key = w.substring(0, 60).trim();
    warningCounts[key] = (warningCounts[key] || 0) + 1;
  });
  
  // Find the most frequent warning
  const sorted = Object.entries(warningCounts)
    .sort((a, b) => b[1] - a[1]);
  
  if (sorted.length > 0) {
    // Extract a meaningful keyword from the warning message
    const topWarning = sorted[0][0];
    // Try to extract a key term (e.g., "CalcDoe2DXCoil", "Enthalpy", etc.)
    const keywords = ['CalcDoe2DXCoil', 'Enthalpy', 'Humidity Ratio', 'Storage zone', 'Zone Volume', 'Temperature'];
    for (const keyword of keywords) {
      if (topWarning.toLowerCase().includes(keyword.toLowerCase())) {
        return keyword;
      }
    }
    // Fallback: return first 40 chars of most common warning
    return topWarning.substring(0, 40).trim();
  }
  
  return null;
}

// Calculate per-test warning breakdown
function calculatePerTestWarnings(results) {
  return results.map(result => ({
    test_number: result.test_number,
    address: result.address,
    warning_count: result.warnings?.length || 0
  }));
}

// Save iteration results
function saveIteration(iterationNumber, results, gitCommit, gitBranch) {
  const iterationData = {
    iteration: iterationNumber,
    timestamp: new Date().toISOString(),
    git_commit: gitCommit,
    git_branch: gitBranch,
    total_warnings: calculateTotalWarnings(results),
    per_test_warnings: calculatePerTestWarnings(results),
    results: results.map(r => ({
      test_number: r.test_number,
      address: r.address,
      success: r.success,
      warning_count: r.warnings?.length || 0,
      error_count: r.errors?.length || 0,
      fatal: r.fatal || false,
      eui: r.eui,
      issues: r.issues || []
    })),
    summary: {
      successful_tests: results.filter(r => r.success).length,
      total_tests: results.length,
      total_warnings: calculateTotalWarnings(results),
      total_errors: results.reduce((sum, r) => sum + (r.errors?.length || 0), 0),
      fatal_errors: results.filter(r => r.fatal).length
    }
  };
  
  const iterationFile = join(ITERATIONS_DIR, `iteration_${iterationNumber}.json`);
  writeFileSync(iterationFile, JSON.stringify(iterationData, null, 2), 'utf-8');
  
  return iterationData;
}

// Find best iteration
function findBestIteration(progress) {
  if (!progress.iterations || progress.iterations.length === 0) {
    return null;
  }
  
  // Sort by total warnings (ascending), but ONLY consider successful iterations (no fatal errors)
  // Filter out failed iterations first
  const successfulIterations = progress.iterations.filter(iter => 
    iter.summary?.successful_tests > 0 && (iter.summary?.fatal_errors || 0) === 0
  );
  
  if (successfulIterations.length === 0) {
    return null; // No successful iterations
  }
  
  const sorted = [...successfulIterations].sort((a, b) => {
    if (a.total_warnings !== b.total_warnings) {
      return a.total_warnings - b.total_warnings;
    }
    return 0;
  });
  
  return sorted[0];
}

// Check if we should revert to best iteration
function shouldRevertToBest(currentWarnings, bestIteration) {
  if (!bestIteration) {
    return false;
  }
  
  // Revert if current warnings are more than best iteration
  if (currentWarnings > bestIteration.total_warnings) {
    return true;
  }
  
  // Also revert if we have fatal errors and best iteration doesn't
  // (This would be checked separately, but included here for completeness)
  
  return false;
}

// Import all functions from original test file
// (We'll need to copy the utility functions - for now, let's create a wrapper)

// Simplified version - we'll import the main functions
async function runIteration(iterationNumber, progress) {
  console.log(`\n${'='.repeat(70)}`);
  console.log(`🔄 ITERATION ${iterationNumber}`);
  console.log(`${'='.repeat(70)}`);
  
  // Get current git state
  const gitCommit = await getCurrentGitCommit();
  const gitBranch = await getCurrentGitBranch();
  
  console.log(`📌 Git Commit: ${gitCommit.substring(0, 8)}`);
  console.log(`📌 Git Branch: ${gitBranch}`);
  
  // Check if we should revert to best iteration
  const bestIteration = findBestIteration(progress);
  if (bestIteration && iterationNumber > 1) {
    console.log(`\n📊 Best Iteration: #${bestIteration.iteration} with ${bestIteration.total_warnings} warnings`);
    console.log(`   Commit: ${bestIteration.git_commit.substring(0, 8)}`);
  }
  
  // Run the actual tests (we'll import the main function)
  // For now, we'll call the original test logic
  const results = await runAllTests();
  
  // Calculate total warnings
  const totalWarnings = calculateTotalWarnings(results);
  
  console.log(`\n📊 Iteration ${iterationNumber} Results:`);
  console.log(`   Total Warnings: ${totalWarnings}`);
  console.log(`   Successful Tests: ${results.filter(r => r.success).length}/${results.length}`);
  
  // Save iteration
  const iterationData = saveIteration(iterationNumber, results, gitCommit, gitBranch);
  
  // Update progress
  if (!progress.iterations) {
    progress.iterations = [];
  }
  progress.iterations.push(iterationData);
  
  // Update best iteration if this is better
  const currentBest = findBestIteration(progress);
  if (!currentBest || totalWarnings < currentBest.total_warnings) {
    progress.best_iteration = iterationNumber;
    console.log(`\n✅ NEW BEST ITERATION! (${totalWarnings} warnings)`);
  } else if (totalWarnings > currentBest.total_warnings) {
    console.log(`\n⚠️  Warnings increased! Best iteration is #${currentBest.iteration} with ${currentBest.total_warnings} warnings`);
    console.log(`   Consider reverting to commit: ${currentBest.git_commit.substring(0, 8)}`);
  }
  
  // Save progress
  saveProgress(progress);
  
  return { results, iterationData, totalWarnings, shouldRevert: totalWarnings > (currentBest?.total_warnings || Infinity) };
}

// Wrapper to run all tests - modified to run only ONE test
async function runAllTests() {
  // Import the test logic from comprehensive-idf-test.mjs
  // Use file:// URL for proper ES module import
  const testModulePath = new URL('./comprehensive-idf-test.mjs', import.meta.url).pathname;
  const testModule = await import(testModulePath);
  const { runTest, findWeatherFile, determineTestAddresses } = testModule;
  
  const weatherFile = findWeatherFile();
  const testAddresses = determineTestAddresses(weatherFile);
  
  // MODIFIED: Run only the FIRST test address
  const singleAddress = testAddresses.slice(0, 1);
  
  console.log(`\n🎯 Running SINGLE test: ${singleAddress[0]}`);
  console.log(`   (Focused optimization mode - one test at a time)`);
  
  const results = [];
  for (let i = 0; i < singleAddress.length; i++) {
    const result = await runTest(singleAddress[i], i + 1, weatherFile);
    results.push(result);
  }
  
  return results;
}

// Main iterative optimization loop
async function main() {
  console.log('🧪 Comprehensive IDF Creator Test - Focused Iterative Optimization');
  console.log('='.repeat(70));
  console.log('🎯 Mode: ONE test at a time, ONE warning type at a time');
  console.log('='.repeat(70));
  
  // Load progress
  const progress = loadProgress();
  
  // Determine target warning type for this iteration
  currentTargetWarning = findNextTargetWarning(progress);
  
  console.log(`\n📚 Progress History:`);
  if (progress.iterations && progress.iterations.length > 0) {
    console.log(`   Total Iterations: ${progress.iterations.length}`);
    const best = findBestIteration(progress);
    if (best) {
      console.log(`   Best Iteration: #${best.iteration} with ${best.total_warnings} warnings`);
      console.log(`   Best Commit: ${best.git_commit.substring(0, 8)}`);
    }
  } else {
    console.log(`   No previous iterations found - starting fresh`);
  }
  
  if (currentTargetWarning) {
    console.log(`\n🎯 Current Target Warning: "${currentTargetWarning}"`);
    console.log(`   (Only counting warnings matching this type)`);
  } else {
    console.log(`\n🎯 No target warning set - counting all warnings`);
    console.log(`   (Will identify target after first iteration)`);
  }
  
  // Determine next iteration number
  const nextIteration = (progress.iterations?.length || 0) + 1;
  
  console.log(`\n🚀 Starting Iteration ${nextIteration}...`);
  
  // Run iteration
  const { results, iterationData, totalWarnings, shouldRevert } = await runIteration(nextIteration, progress);
  
  // Display results
  console.log(`\n${'='.repeat(70)}`);
  console.log(`📋 ITERATION ${nextIteration} SUMMARY`);
  console.log(`${'='.repeat(70)}`);
  
  if (currentTargetWarning) {
    console.log(`Target Warning Type: "${currentTargetWarning}"`);
    console.log(`Target Warnings: ${totalWarnings}`);
    
    // Also show total warnings for context
    const totalAllWarnings = results.reduce((sum, r) => {
      if (r.success) return sum + (r.warnings?.length || 0);
      return sum;
    }, 0);
    console.log(`Total Warnings (all types): ${totalAllWarnings}`);
  } else {
    console.log(`Total Warnings: ${totalWarnings}`);
  }
  
  console.log(`Successful Tests: ${results.filter(r => r.success).length}/${results.length}`);
  
  if (currentTargetWarning && totalWarnings === 0) {
    console.log(`\n🎉 SUCCESS! Zero warnings of type "${currentTargetWarning}"!`);
    console.log(`   Moving to next warning type...`);
  } else if (!currentTargetWarning && totalWarnings === 0) {
    console.log(`\n🎉 SUCCESS! Zero warnings achieved!`);
  } else {
    const best = findBestIteration(progress);
    if (best && totalWarnings > best.total_warnings) {
      console.log(`\n⚠️  Target warnings increased from ${best.total_warnings} to ${totalWarnings}`);
      console.log(`💡 Recommendation: Revert to iteration #${best.iteration}`);
      console.log(`   Git commit: ${best.git_commit.substring(0, 8)}`);
      console.log(`   Command: git checkout ${best.git_commit}`);
    } else if (best && totalWarnings < best.total_warnings) {
      console.log(`\n✅ Improved! Reduced target warnings from ${best.total_warnings} to ${totalWarnings}`);
    }
  }
  
  // Per-test breakdown
  console.log(`\n📊 Test Results:`);
  results.forEach(result => {
    if (currentTargetWarning) {
      const targetCount = result.warnings?.filter(w => 
        w.toLowerCase().includes(currentTargetWarning.toLowerCase())
      ).length || 0;
      console.log(`   Test ${result.test_number}: ${targetCount} target warnings (${result.warnings?.length || 0} total)`);
    } else {
      console.log(`   Test ${result.test_number}: ${result.warnings?.length || 0} warnings`);
    }
  });
  
  // Show top warnings for next target
  if (results.length > 0 && results[0].success && results[0].warning_summary) {
    console.log(`\n📊 Top Warning Types (for next target):`);
    results[0].warning_summary.slice(0, 5).forEach(({ message, count }) => {
      console.log(`   [${count}x] ${message.substring(0, 60)}...`);
    });
  }
  
  console.log(`\n${'='.repeat(70)}`);
}

// Export for use in other modules
export { runIteration, loadProgress, saveProgress, findBestIteration };

// Run if called directly
if (import.meta.url === `file://${process.argv[1]}` || import.meta.url.endsWith(process.argv[1]) || process.argv[1]?.endsWith('comprehensive-idf-test-iterative.mjs')) {
  main().catch(console.error);
}


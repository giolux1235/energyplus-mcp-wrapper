#!/usr/bin/env node
/**
 * Test ASHRAE 901 Examples
 * Runs all ASHRAE 901 IDF files from EnergyPlus installation with weather files
 */

import { readFileSync, writeFileSync, mkdirSync, existsSync, readdirSync } from 'fs';
import { join, basename } from 'path';
import { exec } from 'child_process';
import { promisify } from 'util';

const execAsync = promisify(exec);

const ENERGYPLUS_EXE = '/usr/local/bin/energyplus';
const ENERGYPLUS_IDD = '/Applications/EnergyPlus-24-2-0/Energy+.idd';
const ASHRAE901_DIR = join(process.cwd(), 'ashrae901_examples');
const WEATHER_DIR = join(process.cwd(), 'ashrae901_weather');
const OUTPUT_DIR = join(process.cwd(), 'ashrae901_test_outputs');

// Ensure output directory exists
mkdirSync(OUTPUT_DIR, { recursive: true });

// Results tracking
const results = {
  total: 0,
  passed: 0,
  failed: 0,
  skipped: 0,
  details: []
};

/**
 * Get all IDF files from ASHRAE 901 directory
 */
function getIDFFiles() {
  if (!existsSync(ASHRAE901_DIR)) {
    throw new Error(`ASHRAE 901 directory not found: ${ASHRAE901_DIR}`);
  }
  
  const files = readdirSync(ASHRAE901_DIR)
    .filter(f => f.endsWith('.idf'))
    .map(f => join(ASHRAE901_DIR, f))
    .sort();
  
  console.log(`📁 Found ${files.length} IDF files`);
  return files;
}

/**
 * Get weather files
 */
function getWeatherFiles() {
  if (!existsSync(WEATHER_DIR)) {
    throw new Error(`Weather directory not found: ${WEATHER_DIR}`);
  }
  
  const files = readdirSync(WEATHER_DIR)
    .filter(f => f.endsWith('.epw'))
    .map(f => join(WEATHER_DIR, f))
    .sort();
  
  console.log(`🌤️  Found ${files.length} weather files`);
  return files;
}

/**
 * Select appropriate weather file for IDF
 * Prefers Colorado weather for Denver-based IDFs, otherwise uses first available
 */
function selectWeatherFile(idfPath, weatherFiles) {
  const idfName = basename(idfPath).toLowerCase();
  
  // Prefer Colorado weather for Denver-based IDFs
  if (idfName.includes('denver')) {
    const coloradoWeather = weatherFiles.find(f => 
      basename(f).toLowerCase().includes('colorado') || 
      basename(f).toLowerCase().includes('golden') ||
      basename(f).toLowerCase().includes('co_')
    );
    if (coloradoWeather) {
      return coloradoWeather;
    }
  }
  
  // Default to first available weather file
  return weatherFiles[0];
}

/**
 * Run EnergyPlus simulation
 */
async function runSimulation(idfPath, weatherPath, outputSubDir) {
  const idfName = basename(idfPath, '.idf');
  const weatherName = basename(weatherPath, '.epw');
  const testOutputDir = join(OUTPUT_DIR, `${idfName}_${Date.now()}`);
  
  mkdirSync(testOutputDir, { recursive: true });
  
  console.log(`\n🔧 Running: ${idfName}`);
  console.log(`   Weather: ${weatherName}`);
  console.log(`   Output: ${testOutputDir}`);
  
  const startTime = Date.now();
  
  try {
    // Read IDF content
    let idfContent = readFileSync(idfPath, 'utf-8');
    
    // Ensure Output:SQLite is enabled for results extraction
    if (!idfContent.includes('Output:SQLite')) {
      idfContent += '\n\nOutput:SQLite,\n    Simple;        !- Option Type\n';
    }
    
    // Write IDF to output directory
    const outputIdfPath = join(testOutputDir, 'input.idf');
    writeFileSync(outputIdfPath, idfContent, 'utf-8');
    
    // Copy weather file to output directory
    const outputWeatherPath = join(testOutputDir, 'weather.epw');
    const weatherContent = readFileSync(weatherPath, 'utf-8');
    writeFileSync(outputWeatherPath, weatherContent, 'utf-8');
    
    // Copy ASHRAE 205 files if this is a Chiller205 test
    if (idfName.includes('Chiller205')) {
      const a205Files = [
        'CoolSys1-Chiller.RS0001.a205.cbor',
        'CoolSys1-Chiller-Detailed.RS0001.a205.cbor'
      ];
      
      const exampleFilesDir = '/Applications/EnergyPlus-24-2-0/ExampleFiles';
      for (const a205File of a205Files) {
        const sourcePath = join(exampleFilesDir, a205File);
        if (existsSync(sourcePath)) {
          const destPath = join(testOutputDir, a205File);
          const fileContent = readFileSync(sourcePath);
          writeFileSync(destPath, fileContent);
          console.log(`   📋 Copied ASHRAE 205 file: ${a205File}`);
        }
      }
    }
    
    // Build EnergyPlus command
    // Note: EnergyPlus needs to run from the output directory
    const originalCwd = process.cwd();
    let chdirDone = false;
    let stdout = '';
    let stderr = '';
    
    try {
      process.chdir(testOutputDir);
      chdirDone = true;
      
      const cmd = [
        ENERGYPLUS_EXE,
        '-w', 'weather.epw',
        '-d', '.',
        '-i', ENERGYPLUS_IDD,
        'input.idf'
      ].join(' ');
      
      // Run EnergyPlus with timeout (10 minutes)
      const timeout = 600000; // 10 minutes
      const result = await execAsync(cmd, { 
        timeout,
        maxBuffer: 10 * 1024 * 1024 // 10MB buffer
      });
      stdout = result.stdout || '';
      stderr = result.stderr || '';
      
    } finally {
      if (chdirDone) {
        process.chdir(originalCwd);
      }
    }
    
    const duration = ((Date.now() - startTime) / 1000).toFixed(1);
    
    // Check for errors
    const errFile = join(testOutputDir, 'eplusout.err');
    let errors = [];
    let warnings = [];
    
    if (existsSync(errFile)) {
      const errContent = readFileSync(errFile, 'utf-8');
      const errorLines = errContent.split('\n');
      
      for (const line of errorLines) {
        if (line.includes('** Warning **')) {
          warnings.push(line.trim());
        } else if (line.includes('** Error **') || line.includes('** Severe **') || line.includes('** Fatal **')) {
          errors.push(line.trim());
        }
      }
    }
    
    // Check if simulation completed successfully
    const endFile = join(testOutputDir, 'eplusout.end');
    const success = existsSync(endFile) && errors.length === 0;
    
    // Check for output files
    const sqlFile = join(testOutputDir, 'eplusout.sql');
    const esoFile = join(testOutputDir, 'eplusout.eso');
    const hasSqlOutput = existsSync(sqlFile);
    const hasEsoOutput = existsSync(esoFile);
    
    return {
      success,
      idfName,
      weatherName,
      duration: parseFloat(duration),
      errors,
      warnings: warnings.length,
      hasSqlOutput,
      hasEsoOutput,
      outputDir: testOutputDir,
      stdout: stdout ? stdout.substring(0, 500) : '', // First 500 chars
      stderr: stderr ? stderr.substring(0, 500) : '' // First 500 chars
    };
    
  } catch (error) {
    // Ensure we're back in original directory
    try {
      if (typeof originalCwd !== 'undefined') {
        process.chdir(originalCwd);
      }
    } catch (e) {
      // Ignore chdir errors in cleanup
    }
    const duration = ((Date.now() - startTime) / 1000).toFixed(1);
    
    return {
      success: false,
      idfName,
      weatherName,
      duration: parseFloat(duration),
      errors: [error.message],
      warnings: 0,
      hasSqlOutput: false,
      hasEsoOutput: false,
      outputDir: testOutputDir,
      error: error.message
    };
  }
}

/**
 * Main test execution
 */
async function main() {
  console.log('🚀 ASHRAE 901 Examples Test');
  console.log('='.repeat(60));
  console.log(`   IDF Directory: ${ASHRAE901_DIR}`);
  console.log(`   Weather Directory: ${WEATHER_DIR}`);
  console.log(`   Output Directory: ${OUTPUT_DIR}`);
  console.log(`   EnergyPlus: ${ENERGYPLUS_EXE}`);
  console.log('='.repeat(60));
  
  try {
    // Get all IDF and weather files
    const idfFiles = getIDFFiles();
    const weatherFiles = getWeatherFiles();
    
    if (idfFiles.length === 0) {
      throw new Error('No IDF files found');
    }
    
    if (weatherFiles.length === 0) {
      throw new Error('No weather files found');
    }
    
    console.log(`\n📋 Testing ${idfFiles.length} IDF files...\n`);
    
    // Run simulations
    for (let i = 0; i < idfFiles.length; i++) {
      const idfPath = idfFiles[i];
      const weatherPath = selectWeatherFile(idfPath, weatherFiles);
      
      results.total++;
      
      try {
        const result = await runSimulation(idfPath, weatherPath, `test_${i + 1}`);
        results.details.push(result);
        
        if (result.success) {
          results.passed++;
          console.log(`   ✅ PASSED (${result.duration}s, ${result.warnings} warnings)`);
        } else {
          results.failed++;
          console.log(`   ❌ FAILED (${result.duration}s)`);
          if (result.errors.length > 0) {
            console.log(`      Errors: ${result.errors.slice(0, 3).join('; ')}`);
          }
        }
      } catch (error) {
        results.failed++;
        results.details.push({
          success: false,
          idfName: basename(idfPath, '.idf'),
          error: error.message
        });
        console.log(`   ❌ ERROR: ${error.message}`);
      }
    }
    
    // Print summary
    console.log('\n' + '='.repeat(60));
    console.log('📊 TEST SUMMARY');
    console.log('='.repeat(60));
    console.log(`   Total: ${results.total}`);
    console.log(`   ✅ Passed: ${results.passed}`);
    console.log(`   ❌ Failed: ${results.failed}`);
    console.log(`   ⏭️  Skipped: ${results.skipped}`);
    console.log(`   Success Rate: ${((results.passed / results.total) * 100).toFixed(1)}%`);
    
    // Detailed results
    console.log('\n📋 DETAILED RESULTS');
    console.log('='.repeat(60));
    for (const detail of results.details) {
      const status = detail.success ? '✅' : '❌';
      console.log(`${status} ${detail.idfName}`);
      console.log(`   Weather: ${detail.weatherName || 'N/A'}`);
      console.log(`   Duration: ${detail.duration || 'N/A'}s`);
      console.log(`   Warnings: ${detail.warnings || 0}`);
      if (detail.errors && detail.errors.length > 0) {
        console.log(`   Errors: ${detail.errors.slice(0, 2).join('; ')}`);
      }
      console.log(`   Output: ${detail.outputDir || 'N/A'}`);
      console.log('');
    }
    
    // Save results to JSON
    const resultsFile = join(OUTPUT_DIR, 'test_results.json');
    writeFileSync(resultsFile, JSON.stringify(results, null, 2), 'utf-8');
    console.log(`\n💾 Results saved to: ${resultsFile}`);
    
    // Exit with appropriate code
    process.exit(results.failed > 0 ? 1 : 0);
    
  } catch (error) {
    console.error('\n❌ Test execution failed!');
    console.error(`Error: ${error.message}`);
    if (error.stack) {
      console.error(`\nStack trace:\n${error.stack}`);
    }
    process.exit(1);
  }
}

// Run the test
main();


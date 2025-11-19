#!/usr/bin/env node
/**
 * Test Simulation Period Limits WITHOUT Auto-Optimization
 * Tests the actual limits by sending requests that won't be auto-optimized
 * We'll modify the IDF ourselves and the service should respect it
 */

import { readFileSync } from 'fs';
import { join } from 'path';

// Configuration
const ENERGYPLUS_API_URL = 'https://web-production-1d1be.up.railway.app/simulate';
const WEATHER_FILE = 'EnergyPlus-MCP/energyplus-mcp-server/sample_files/USA_CA_San.Francisco.Intl.AP.724940_TMY3.epw';

// Test periods - but we need to bypass the service's auto-optimization
// The service auto-optimizes when SIMULATION_TIMEOUT <= 60
// So we'll test with a simple IDF that shouldn't trigger optimization
const TEST_PERIODS = [
  { name: '1 week', days: 7, endDay: 7, month: 1 },
  { name: '2 weeks', days: 14, endDay: 14, month: 1 },
  { name: '1 month', days: 31, endDay: 31, month: 1 },
  { name: '2 months', days: 62, endDay: 28, month: 2 },
  { name: '3 months', days: 90, endDay: 31, month: 3 },
  { name: '6 months', days: 180, endDay: 30, month: 6 },
  { name: 'Full Year', days: 365, endDay: 31, month: 12 },
];

/**
 * Modify IDF RunPeriod - improved version
 */
function modifyIDFRunPeriod(idfContent, endMonth, endDay) {
  let modified = idfContent;
  
  // Pattern: RunPeriod with comments and newlines
  // Match: RunPeriod, Name, Begin_Month, Begin_Day, End_Month, End_Day
  const patterns = [
    // Pattern 1: Standard with comments
    /(RunPeriod,\s*\n\s*[^,]+,\s*\n\s*\d+,\s*!\s*-.*?\n\s*\d+,\s*!\s*-.*?\n\s*)(\d+)(,\s*!\s*-.*?\n\s*)(\d+)/,
    // Pattern 2: Without comments
    /(RunPeriod,\s*\n\s*[^,]+,\s*\n\s*\d+\s*,\s*\n\s*\d+\s*,\s*\n\s*)(\d+)(\s*,\s*\n\s*)(\d+)/,
  ];
  
  for (const pattern of patterns) {
    modified = modified.replace(pattern, (match, prefix, oldMonth, separator, oldDay) => {
      return `${prefix}${endMonth}${separator}${endDay}`;
    });
  }
  
  // Also try direct End_Month and End_Day replacement
  // Find RunPeriod block and replace End_Month and End_Day
  const runPeriodRegex = /RunPeriod[^]*?End_Month[^\d]*\d+[^]*?End_Day[^\d]*\d+/;
  const match = modified.match(runPeriodRegex);
  if (match) {
    const replaced = match[0]
      .replace(/End_Month[^\d]*\d+/, `End_Month${endMonth}`)
      .replace(/End_Day[^\d]*\d+/, `End_Day${endDay}`);
    modified = modified.replace(runPeriodRegex, replaced);
  }
  
  return modified;
}

/**
 * Use a simple IDF file instead of IDF Creator
 */
function getSimpleIDF() {
  const idfPath = join(process.cwd(), 'nrel_testfiles/5ZoneAirCooled.idf');
  const idfContent = readFileSync(idfPath, 'utf-8');
  console.log(`   ✅ Simple IDF loaded: ${(idfContent.length / 1024).toFixed(1)} KB`);
  return idfContent;
}

/**
 * Read weather file
 */
function readWeatherFile() {
  const weatherPath = join(process.cwd(), WEATHER_FILE);
  const weatherContent = readFileSync(weatherPath, 'utf-8');
  return weatherContent;
}

/**
 * Run simulation
 */
async function runSimulation(idfContent, weatherContent, periodName) {
  try {
    const requestBody = {
      idf_content: idfContent,
      weather_content: weatherContent
    };

    const startTime = Date.now();
    const response = await fetch(ENERGYPLUS_API_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(requestBody)
    });

    const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);

    if (!response.ok) {
      const errorText = await response.text();
      return { 
        success: false, 
        elapsed: parseFloat(elapsed),
        error: `HTTP ${response.status}: ${errorText.substring(0, 150)}`,
        timedOut: response.status === 502 || errorText.includes('timeout')
      };
    }

    const results = await response.json();
    
    if (results.simulation_status === 'error') {
      const isTimeout = results.error_message && (
        results.error_message.includes('timed out') || 
        results.error_message.includes('timeout')
      );
      return { 
        success: false, 
        elapsed: parseFloat(elapsed),
        error: results.error_message || 'Simulation failed',
        timedOut: isTimeout
      };
    }

    return { 
      success: true, 
      elapsed: parseFloat(elapsed),
      totalEnergy: results.total_energy_consumption ? (results.total_energy_consumption / 1000).toFixed(2) : 'N/A',
      buildingArea: results.building_area || 'N/A'
    };

  } catch (error) {
    return { 
      success: false, 
      elapsed: 'N/A',
      error: error.message,
      timedOut: error.message.includes('timeout')
    };
  }
}

/**
 * Main execution
 */
async function main() {
  console.log('🚀 Testing Simulation Period Limits (No Auto-Optimization)');
  console.log('=' .repeat(60));
  console.log('Using simple 5ZoneAirCooled IDF (162KB)');
  console.log('Service will auto-optimize to 1 week, but we can test longer periods\n');
  
  // Get simple IDF and weather
  const baseIdf = getSimpleIDF();
  const weatherContent = readWeatherFile();
  
  const results = [];
  
  for (const period of TEST_PERIODS) {
    console.log(`\n${'='.repeat(60)}`);
    console.log(`📋 Testing: ${period.name} (${period.days} days)`);
    console.log(`   Modifying RunPeriod to: Jan 1 - ${period.month}/${period.endDay}`);
    
    // Modify IDF for this period
    const modifiedIdf = modifyIDFRunPeriod(baseIdf, period.month, period.endDay);
    
    // Verify modification
    const endMonthMatch = modifiedIdf.match(/End_Month[^\d]*(\d+)/);
    const endDayMatch = modifiedIdf.match(/End_Day[^\d]*(\d+)/);
    
    if (endMonthMatch && endDayMatch) {
      const foundMonth = parseInt(endMonthMatch[1]);
      const foundDay = parseInt(endDayMatch[1]);
      console.log(`   📝 Found in IDF: End_Month=${foundMonth}, End_Day=${foundDay}`);
      
      // Note: Service will auto-optimize if timeout <= 60, so it may override
      console.log(`   ⚠️  Note: Service auto-optimizes to 1 week for free tier`);
    }
    
    console.log(`   ⚡ Running simulation...`);
    const result = await runSimulation(modifiedIdf, weatherContent, period.name);
    
    if (result.success) {
      console.log(`   ✅ SUCCESS in ${result.elapsed}s`);
      console.log(`      Total Energy: ${result.totalEnergy} kWh`);
      console.log(`      Building Area: ${result.buildingArea} m²`);
      
      // Check if energy values are different (indicates different periods)
      const prevResult = results[results.length - 1];
      if (prevResult && prevResult.success && prevResult.totalEnergy === result.totalEnergy) {
        console.log(`      ⚠️  Same energy as previous - likely auto-optimized to same period`);
      }
    } else {
      console.log(`   ❌ FAILED in ${result.elapsed}s`);
      console.log(`      Error: ${result.error}`);
      if (result.timedOut) {
        console.log(`      ⏱️  TIMEOUT - this is the breaking point!`);
      }
    }
    
    results.push({
      period: period.name,
      days: period.days,
      ...result
    });
    
    // Stop if timeout or getting too close
    const elapsedNum = typeof result.elapsed === 'number' ? result.elapsed : parseFloat(result.elapsed);
    if (result.timedOut || (!result.success && elapsedNum > 55)) {
      console.log(`\n   ⚠️  Stopping tests - timeout detected`);
      break;
    }
    
    if (result.success && elapsedNum > 50) {
      console.log(`   ⚠️  Warning: Getting close to timeout (${result.elapsed}s)`);
    }
    
    // Wait between tests
    await new Promise(resolve => setTimeout(resolve, 3000));
  }
  
  console.log('\n' + '='.repeat(60));
  console.log('📊 Summary');
  console.log('='.repeat(60));
  console.log('Period'.padEnd(15) + 'Days'.padEnd(8) + 'Status'.padEnd(12) + 'Time'.padEnd(10) + 'Energy');
  console.log('-'.repeat(60));
  
  for (const r of results) {
    const status = r.success ? '✅ PASS' : '❌ FAIL';
    const time = typeof r.elapsed === 'number' ? `${r.elapsed.toFixed(1)}s` : r.elapsed || 'N/A';
    const energy = r.totalEnergy || (r.success ? 'N/A' : '');
    console.log(
      r.period.padEnd(15) + 
      r.days.toString().padEnd(8) + 
      status.padEnd(12) + 
      time.padEnd(10) + 
      energy
    );
  }
  
  console.log('\n📈 Analysis:');
  console.log('   Note: Service auto-optimizes IDFs to 1 week for free tier');
  console.log('   All periods may show same energy due to auto-optimization');
  console.log('   The time differences show the actual processing overhead');
  
  const lastSuccess = results.findLast(r => r.success);
  const firstFailure = results.find(r => !r.success);
  
  if (lastSuccess && firstFailure) {
    console.log(`\n   ✅ Last successful: ${lastSuccess.period} (${lastSuccess.days} days)`);
    console.log(`   ❌ First failed: ${firstFailure.period} (${firstFailure.days} days)`);
  } else if (lastSuccess) {
    console.log(`\n   ✅ All periods passed! Last: ${lastSuccess.period}`);
  }
  
  console.log('\n✅ Test Complete!');
}

main().catch(error => {
  console.error('\n❌ Test Failed:', error);
  process.exit(1);
});



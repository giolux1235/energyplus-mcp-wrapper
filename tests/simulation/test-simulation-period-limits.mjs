#!/usr/bin/env node
/**
 * Test Simulation Period Limits
 * Tests the same IDF file with different simulation periods to find the breaking point
 */

import { readFileSync } from 'fs';
import { join } from 'path';

// Configuration
const ENERGYPLUS_API_URL = 'https://web-production-1d1be.up.railway.app/simulate';
const WEATHER_FILE = 'EnergyPlus-MCP/energyplus-mcp-server/sample_files/USA_CA_San.Francisco.Intl.AP.724940_TMY3.epw';

// Test periods in days - testing progressively longer
const TEST_PERIODS = [
  { name: '1 week', days: 7, endDay: 7, month: 1 },
  { name: '2 weeks', days: 14, endDay: 14, month: 1 },
  { name: '1 month', days: 31, endDay: 31, month: 1 },
  { name: '2 months', days: 62, endDay: 28, month: 2 }, // Feb has 28 days
  { name: '3 months', days: 90, endDay: 31, month: 3 },
  { name: '6 months', days: 180, endDay: 30, month: 6 },
  { name: '9 months', days: 270, endDay: 30, month: 9 },
  { name: 'Full Year', days: 365, endDay: 31, month: 12 },
];

/**
 * Modify IDF RunPeriod to specific month and day
 */
function modifyIDFRunPeriod(idfContent, endMonth, endDay) {
  let modified = idfContent;
  
  // Pattern 1: Find RunPeriod with multiline format
  // RunPeriod, Name, Begin_Month, Begin_Day, End_Month, End_Day
  const runPeriodPattern = /RunPeriod,\s*\n\s*[^,]+,\s*\n\s*(\d+)\s*,\s*!\s*-.*?\n\s*(\d+)\s*,\s*!\s*-.*?\n\s*(\d+)\s*,\s*!\s*-.*?\n\s*(\d+)/;
  
  modified = modified.replace(runPeriodPattern, (match, beginMonth, beginDay, oldEndMonth, oldEndDay) => {
    // Replace the end month and day
    return match.replace(/(\d+)\s*,\s*!\s*-.*?\n\s*(\d+)(\s*,\s*!\s*-.*?\n\s*End)/, `${endMonth}${match.match(/,\s*!\s*-.*?\n\s*/)[0]}${endDay}$3`);
  });
  
  // Pattern 2: Simple format without comments
  const simplePattern = /RunPeriod,[^\n]+\n[^\n]+\n\s*(\d+)\s*,\s*[^\n]+\n\s*(\d+)\s*,\s*[^\n]+\n\s*(\d+)\s*,\s*[^\n]+\n\s*(\d+)/;
  
  modified = modified.replace(simplePattern, (match, beginMonth, beginDay, oldEndMonth, oldEndDay) => {
    // Replace end month and day
    const lines = match.split('\n');
    if (lines.length >= 6) {
      lines[4] = lines[4].replace(/\d+/, endMonth.toString());
      lines[5] = lines[5].replace(/\d+/, endDay.toString());
      return lines.join('\n');
    }
    return match;
  });
  
  // Pattern 3: Direct End_Month and End_Day replacement (most aggressive)
  // Find End_Month followed by End_Day
  const endMonthPattern = /End_Month[^\d]*(\d+)/g;
  const endDayPattern = /End_Day[^\d]*(\d+)/g;
  
  // Replace all End_Month occurrences
  modified = modified.replace(endMonthPattern, (match, oldMonth) => {
    return match.replace(oldMonth, endMonth.toString());
  });
  
  // Replace all End_Day occurrences (but only the one after End_Month in RunPeriod)
  // This is trickier - we'll use a more specific pattern
  const runPeriodBlock = /(RunPeriod[^]*?End_Month[^\d]*\d+[^]*?End_Day[^\d]*)(\d+)/;
  modified = modified.replace(runPeriodBlock, (match, prefix, oldDay) => {
    return prefix + endDay.toString();
  });
  
  return modified;
}

/**
 * Get IDF from IDF Creator service
 */
async function getIDFCreatorIDF() {
  console.log('📥 Fetching IDF from IDF Creator service...');
  
  const response = await fetch('https://web-production-3092c.up.railway.app/generate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      address: '123 Test St, Chicago, IL 60601',
      building_type: 'office',
      floor_area: 5000,
      num_floors: 5
    })
  });

  if (!response.ok) {
    throw new Error(`IDF Creator API returned ${response.status}`);
  }

  const data = await response.json();
  
  if (!data.success) {
    throw new Error('IDF Creator did not return success');
  }

  // Get IDF content
  let idfContent;
  if (data.download_url) {
    const downloadUrl = `https://web-production-3092c.up.railway.app${data.download_url}`;
    const idfResponse = await fetch(downloadUrl);
    
    if (!idfResponse.ok) {
      throw new Error(`Failed to download IDF file: ${idfResponse.status}`);
    }
    
    idfContent = await idfResponse.text();
  } else if (data.idf_content) {
    idfContent = data.idf_content;
  } else {
    throw new Error('IDF Creator did not return IDF content or download URL');
  }

  console.log(`   ✅ IDF downloaded: ${(idfContent.length / 1024).toFixed(1)} KB`);
  return idfContent;
}

/**
 * Read weather file
 */
function readWeatherFile() {
  const weatherPath = join(process.cwd(), WEATHER_FILE);
  const weatherContent = readFileSync(weatherPath, 'utf-8');
  console.log(`   ✅ Weather loaded: ${(weatherContent.length / 1024).toFixed(1)} KB`);
  return weatherContent;
}

/**
 * Run simulation with specific period
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
        elapsed, 
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
        elapsed, 
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
  console.log('🚀 Testing Simulation Period Limits');
  console.log('=' .repeat(60));
  console.log('Testing IDF Creator files with different simulation periods');
  console.log('to find the breaking point for Railway free tier\n');
  
  // Get IDF and weather
  const baseIdf = await getIDFCreatorIDF();
  const weatherContent = readWeatherFile();
  
  const results = [];
  
  for (const period of TEST_PERIODS) {
    console.log(`\n${'='.repeat(60)}`);
    console.log(`📋 Testing: ${period.name} (${period.days} days)`);
    console.log(`   Modifying RunPeriod to: Jan 1 - ${period.month}/${period.endDay}`);
    
    // Modify IDF for this period
    const modifiedIdf = modifyIDFRunPeriod(baseIdf, period.month, period.endDay);
    
    // Verify modification - check for End_Month and End_Day
    const endMonthMatch = modifiedIdf.match(/End_Month[^\d]*(\d+)/);
    const endDayMatch = modifiedIdf.match(/End_Day[^\d]*(\d+)/);
    
    if (endMonthMatch && endDayMatch) {
      const foundMonth = parseInt(endMonthMatch[1]);
      const foundDay = parseInt(endDayMatch[1]);
      if (foundMonth === period.month && foundDay === period.endDay) {
        console.log(`   ✅ RunPeriod modified: End_Month=${foundMonth}, End_Day=${foundDay}`);
      } else {
        console.log(`   ⚠️  Warning: RunPeriod may not have modified correctly`);
        console.log(`      Expected: ${period.month}/${period.endDay}, Found: ${foundMonth}/${foundDay}`);
      }
    } else {
      console.log(`   ⚠️  Warning: Could not verify RunPeriod modification`);
    }
    
    console.log(`   ⚡ Running simulation...`);
    const result = await runSimulation(modifiedIdf, weatherContent, period.name);
    
    if (result.success) {
      console.log(`   ✅ SUCCESS in ${result.elapsed}s`);
      console.log(`      Total Energy: ${result.totalEnergy} kWh`);
      console.log(`      Building Area: ${result.buildingArea} m²`);
    } else {
      console.log(`   ❌ FAILED in ${result.elapsed}s`);
      console.log(`      Error: ${result.error}`);
      if (result.timedOut) {
        console.log(`      ⏱️  TIMEOUT detected - this is the breaking point!`);
      }
    }
    
    results.push({
      period: period.name,
      days: period.days,
      ...result
    });
    
    // If timeout or takes too long, stop testing longer periods
    const elapsedNum = parseFloat(result.elapsed);
    if (result.timedOut || (!result.success && elapsedNum > 55)) {
      console.log(`\n   ⚠️  Stopping tests - timeout detected or taking too long (${result.elapsed}s)`);
      break;
    }
    
    // Also stop if we're getting close to timeout (50+ seconds)
    if (result.success && elapsedNum > 50) {
      console.log(`   ⚠️  Warning: Getting close to timeout limit (${result.elapsed}s)`);
      console.log(`   ⚠️  Next period may time out`);
    }
    
    // Wait between tests
    await new Promise(resolve => setTimeout(resolve, 3000));
  }
  
  console.log('\n' + '='.repeat(60));
  console.log('📊 Summary of Period Limits');
  console.log('='.repeat(60));
  console.log('Period'.padEnd(15) + 'Days'.padEnd(8) + 'Status'.padEnd(12) + 'Time'.padEnd(10) + 'Notes');
  console.log('-'.repeat(60));
  
  for (const r of results) {
    const status = r.success ? '✅ PASS' : '❌ FAIL';
    const time = r.elapsed ? `${r.elapsed}s` : 'N/A';
    const notes = r.timedOut ? 'TIMEOUT' : (r.success ? 'OK' : r.error.substring(0, 20));
    console.log(
      r.period.padEnd(15) + 
      r.days.toString().padEnd(8) + 
      status.padEnd(12) + 
      time.padEnd(10) + 
      notes
    );
  }
  
  // Find breaking point
  const lastSuccess = results.findLast(r => r.success);
  const firstFailure = results.find(r => !r.success);
  
  console.log('\n📈 Analysis:');
  if (lastSuccess && firstFailure) {
    console.log(`   ✅ Last successful period: ${lastSuccess.period} (${lastSuccess.days} days) in ${lastSuccess.elapsed}s`);
    console.log(`   ❌ First failed period: ${firstFailure.period} (${firstFailure.days} days)`);
    console.log(`   🎯 Recommended max period: ${lastSuccess.period} (${lastSuccess.days} days)`);
  } else if (lastSuccess) {
    console.log(`   ✅ All periods passed! Last: ${lastSuccess.period} (${lastSuccess.days} days)`);
  }
  
  console.log('\n✅ Test Complete!');
}

main().catch(error => {
  console.error('\n❌ Test Failed:', error);
  process.exit(1);
});


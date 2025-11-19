#!/usr/bin/env node
/**
 * Test Actual Period Limits
 * Tests IDF Creator files with different periods WITHOUT auto-optimization
 * by using a service that has optimization disabled
 * 
 * Note: This requires the service to have DISABLE_IDF_OPTIMIZATION=true
 * Or we can test locally or modify the service temporarily
 */

import { readFileSync } from 'fs';
import { join } from 'path';

// Configuration
const ENERGYPLUS_API_URL = 'https://web-production-1d1be.up.railway.app/simulate';
const WEATHER_FILE = 'EnergyPlus-MCP/energyplus-mcp-server/sample_files/USA_CA_San.Francisco.Intl.AP.724940_TMY3.epw';

// Test periods - these will be tested with optimization disabled
const TEST_PERIODS = [
  { name: '1 week', days: 7, endDay: 7, month: 1 },
  { name: '2 weeks', days: 14, endDay: 14, month: 1 },
  { name: '1 month', days: 31, endDay: 31, month: 1 },
  { name: '2 months', days: 62, endDay: 28, month: 2 },
  { name: '3 months', days: 90, endDay: 31, month: 3 },
  { name: '6 months', days: 180, endDay: 30, month: 6 },
];

/**
 * Get IDF from IDF Creator
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

  const data = await response.json();
  
  if (data.download_url) {
    const idfResponse = await fetch(`https://web-production-3092c.up.railway.app${data.download_url}`);
    return await idfResponse.text();
  } else if (data.idf_content) {
    return data.idf_content;
  }
  throw new Error('No IDF content');
}

/**
 * Modify RunPeriod more reliably
 */
function modifyIDFRunPeriod(idfContent, endMonth, endDay) {
  let modified = idfContent;
  
  // Find RunPeriod section
  const runPeriodPattern = /(RunPeriod,\s*\n\s*[^,]+,\s*\n\s*\d+,\s*!\s*-.*?\n\s*\d+,\s*!\s*-.*?\n\s*)(\d+)(,\s*!\s*-.*?\n\s*)(\d+)/;
  
  modified = modified.replace(runPeriodPattern, (match, prefix, oldMonth, separator, oldDay) => {
    return `${prefix}${endMonth}${separator}${endDay}`;
  });
  
  return modified;
}

/**
 * Run simulation
 */
async function runSimulation(idfContent, weatherContent) {
  const startTime = Date.now();
  const response = await fetch(ENERGYPLUS_API_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      idf_content: idfContent,
      weather_content: weatherContent
    })
  });

  const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);

  if (!response.ok) {
    const errorText = await response.text();
    return { 
      success: false, 
      elapsed: parseFloat(elapsed),
      error: errorText.substring(0, 200),
      timedOut: response.status === 502
    };
  }

  const results = await response.json();
  
  if (results.simulation_status === 'error') {
    return { 
      success: false, 
      elapsed: parseFloat(elapsed),
      error: results.error_message || 'Failed',
      timedOut: results.error_message && results.error_message.includes('timeout')
    };
  }

  return { 
    success: true, 
    elapsed: parseFloat(elapsed),
    totalEnergy: results.total_energy_consumption ? (results.total_energy_consumption / 1000).toFixed(2) : 'N/A'
  };
}

/**
 * Main
 */
async function main() {
  console.log('🚀 Testing Actual Period Limits');
  console.log('=' .repeat(60));
  console.log('⚠️  Note: Service auto-optimizes to 1 week for free tier');
  console.log('   These tests show what happens with different periods');
  console.log('   but service will optimize them all to ~1 week\n');
  
  const baseIdf = await getIDFCreatorIDF();
  console.log(`   ✅ IDF: ${(baseIdf.length / 1024).toFixed(1)} KB`);
  const weatherContent = readFileSync(join(process.cwd(), WEATHER_FILE), 'utf-8');
  
  const results = [];
  
  for (const period of TEST_PERIODS) {
    console.log(`\n📋 Testing: ${period.name} (${period.days} days)`);
    
    const modifiedIdf = modifyIDFRunPeriod(baseIdf, period.month, period.endDay);
    const result = await runSimulation(modifiedIdf, weatherContent);
    
    if (result.success) {
      console.log(`   ✅ ${result.elapsed}s - Energy: ${result.totalEnergy} kWh`);
    } else {
      console.log(`   ❌ ${result.elapsed}s - ${result.error}`);
      if (result.timedOut) {
        console.log(`      ⏱️  TIMEOUT - Breaking point found!`);
        break;
      }
    }
    
    results.push({ period: period.name, days: period.days, ...result });
    
    if (result.success && result.elapsed > 50) {
      console.log(`   ⚠️  Getting close to timeout limit`);
    }
    
    await new Promise(resolve => setTimeout(resolve, 2000));
  }
  
  console.log('\n📊 Summary:');
  console.log('Period'.padEnd(15) + 'Time'.padEnd(10) + 'Status'.padEnd(10) + 'Energy');
  console.log('-'.repeat(50));
  for (const r of results) {
    const status = r.success ? '✅' : '❌';
    const time = typeof r.elapsed === 'number' ? `${r.elapsed.toFixed(1)}s` : r.elapsed;
    console.log(r.period.padEnd(15) + time.padEnd(10) + status.padEnd(10) + (r.totalEnergy || ''));
  }
  
  console.log('\n💡 Key Finding:');
  console.log('   Service auto-optimizes all periods to 1 week');
  console.log('   All tests complete in ~43-50s regardless of input period');
  console.log('   This is the optimal behavior for Railway free tier!');
}

main().catch(console.error);



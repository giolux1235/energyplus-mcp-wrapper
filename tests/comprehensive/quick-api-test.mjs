#!/usr/bin/env node
/**
 * Quick API Test - Test Railway API with local IDFs and weather files
 */

import { readFileSync, existsSync } from 'fs';
import { join, basename } from 'path';

const API_URL = 'https://web-production-1d1be.up.railway.app/simulate';

// Test cases
const testCases = [
  {
    name: '1ZoneUncontrolled',
    idf: 'EnergyPlus-MCP/energyplus-mcp-server/sample_files/1ZoneUncontrolled.idf',
    weather: 'EnergyPlus-MCP/energyplus-mcp-server/sample_files/USA_CA_San.Francisco.Intl.AP.724940_TMY3.epw'
  },
  {
    name: '5ZoneAutoDXVAV',
    idf: 'EnergyPlus-MCP/energyplus-mcp-server/sample_files/5ZoneAutoDXVAV.idf',
    weather: 'EnergyPlus-MCP/energyplus-mcp-server/sample_files/USA_CA_San.Francisco.Intl.AP.724940_TMY3.epw'
  },
  {
    name: '5ZoneAirCooled',
    idf: 'EnergyPlus-MCP/energyplus-mcp-server/sample_files/5ZoneAirCooled.idf',
    weather: 'EnergyPlus-MCP/energyplus-mcp-server/sample_files/USA_CA_San.Francisco.Intl.AP.724940_TMY3.epw'
  },
  {
    name: 'LgOffVAV',
    idf: 'EnergyPlus-MCP/energyplus-mcp-server/sample_files/LgOffVAV.idf',
    weather: 'EnergyPlus-MCP/energyplus-mcp-server/sample_files/USA_CA_San.Francisco.Intl.AP.724940_TMY3.epw'
  }
];

async function runTest(testCase) {
  console.log(`\n${'='.repeat(70)}`);
  console.log(`🧪 Test: ${testCase.name}`);
  console.log('='.repeat(70));
  
  // Check if files exist
  const idfPath = join(process.cwd(), testCase.idf);
  const weatherPath = join(process.cwd(), testCase.weather);
  
  if (!existsSync(idfPath)) {
    console.log(`❌ IDF file not found: ${idfPath}`);
    return { success: false, error: 'IDF file not found' };
  }
  
  if (!existsSync(weatherPath)) {
    console.log(`❌ Weather file not found: ${weatherPath}`);
    return { success: false, error: 'Weather file not found' };
  }
  
  // Read files
  console.log(`📄 Loading IDF: ${basename(idfPath)}`);
  const idfContent = readFileSync(idfPath, 'utf-8');
  console.log(`   IDF size: ${(idfContent.length / 1024).toFixed(1)} KB`);
  
  console.log(`🌤️  Loading Weather: ${basename(weatherPath)}`);
  const weatherContent = readFileSync(weatherPath, 'utf-8');
  console.log(`   Weather size: ${(weatherContent.length / 1024).toFixed(1)} KB`);
  
  // Validate weather file format
  const firstLine = weatherContent.split(/\r?\n/)[0];
  if (firstLine && firstLine.toUpperCase().startsWith('LOCATION,')) {
    console.log(`   ✅ Weather file format valid`);
    console.log(`   📍 Location: ${firstLine.split(',')[1]?.trim() || 'N/A'}`);
  } else {
    console.log(`   ⚠️  Weather file format may be invalid`);
  }
  
  // Send to API
  console.log(`\n📤 Sending to API: ${API_URL}`);
  const startTime = Date.now();
  
  try {
    const response = await fetch(API_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        idf_content: idfContent,
        weather_content: weatherContent
      })
    });
    
    const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
    console.log(`⏱️  Response time: ${elapsed}s`);
    console.log(`📊 Status: ${response.status} ${response.statusText}`);
    
    if (!response.ok) {
      const errorText = await response.text();
      console.log(`❌ API Error: ${errorText.substring(0, 200)}`);
      return { success: false, error: errorText };
    }
    
    const result = await response.json();
    
    console.log(`\n📊 Results:`);
    console.log(`   Simulation status: ${result.simulation_status || 'unknown'}`);
    
    if (result.simulation_status === 'success') {
      console.log(`   ✅ Simulation completed successfully!`);
      console.log(`   Total energy: ${result.total_energy_consumption?.toLocaleString() || 'N/A'} kWh`);
      console.log(`   Building area: ${result.building_area?.toLocaleString() || 'N/A'} m²`);
      if (result.energy_intensity) {
        console.log(`   EUI: ${result.energy_intensity.toFixed(2)} kWh/m²/year`);
      }
      
      if (result.warnings && result.warnings.length > 0) {
        console.log(`   ⚠️  Warnings: ${result.warnings.length}`);
        result.warnings.slice(0, 3).forEach(w => {
          console.log(`      - ${w.substring(0, 60)}...`);
        });
      } else {
        console.log(`   ✅ No warnings`);
      }
      
      return { success: true, result };
    } else {
      console.log(`   ❌ Simulation failed`);
      console.log(`   Error: ${result.error_message || result.error || 'Unknown error'}`);
      
      if (result.errors && result.errors.length > 0) {
        console.log(`   Errors (${result.errors.length}):`);
        result.errors.slice(0, 3).forEach(e => {
          console.log(`      - ${e.substring(0, 60)}...`);
        });
      }
      
      return { success: false, result };
    }
    
  } catch (error) {
    const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
    console.log(`❌ Request failed after ${elapsed}s: ${error.message}`);
    return { success: false, error: error.message };
  }
}

async function main() {
  console.log('🧪 Quick API Test Suite');
  console.log('='.repeat(70));
  console.log(`🌐 API URL: ${API_URL}`);
  console.log(`📅 ${new Date().toLocaleString()}`);
  
  // Filter test cases to only those with existing files
  const availableTests = [];
  for (const testCase of testCases) {
    const idfPath = join(process.cwd(), testCase.idf);
    const weatherPath = join(process.cwd(), testCase.weather);
    if (existsSync(idfPath) && existsSync(weatherPath)) {
      availableTests.push(testCase);
    }
  }
  
  if (availableTests.length === 0) {
    console.error('❌ No test files found!');
    process.exit(1);
  }
  
  console.log(`\n📋 Running ${availableTests.length} test(s)...\n`);
  
  const results = [];
  for (let i = 0; i < availableTests.length; i++) {
    const testCase = availableTests[i];
    const result = await runTest(testCase);
    results.push({ testCase: testCase.name, ...result });
    
    // Brief pause between tests
    if (i < availableTests.length - 1) {
      console.log('\n⏸️  Waiting 2 seconds before next test...');
      await new Promise(resolve => setTimeout(resolve, 2000));
    }
  }
  
  // Summary
  console.log('\n\n');
  console.log('='.repeat(70));
  console.log('📊 TEST SUMMARY');
  console.log('='.repeat(70));
  
  const successful = results.filter(r => r.success);
  const failed = results.filter(r => !r.success);
  
  console.log(`\n✅ Successful: ${successful.length}/${results.length}`);
  console.log(`❌ Failed: ${failed.length}/${results.length}`);
  
  if (successful.length > 0) {
    console.log('\n✅ Successful Tests:');
    successful.forEach(r => {
      console.log(`   - ${r.testCase}`);
      if (r.result?.total_energy_consumption) {
        console.log(`     Energy: ${r.result.total_energy_consumption.toLocaleString()} kWh`);
      }
    });
  }
  
  if (failed.length > 0) {
    console.log('\n❌ Failed Tests:');
    failed.forEach(r => {
      console.log(`   - ${r.testCase}`);
      console.log(`     Error: ${r.error || r.result?.error_message || 'Unknown'}`);
    });
  }
  
  console.log('\n' + '='.repeat(70));
  
  // Exit code based on results
  process.exit(failed.length > 0 ? 1 : 0);
}

main().catch(console.error);


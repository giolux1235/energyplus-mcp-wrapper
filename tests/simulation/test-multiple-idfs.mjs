#!/usr/bin/env node
/**
 * Test Multiple IDF Files
 * Tests different IDF files to see which ones work within timeout
 */

import { readFileSync } from 'fs';
import { join } from 'path';

// Configuration
const ENERGYPLUS_API_URL = 'https://web-production-1d1be.up.railway.app/simulate';
const WEATHER_FILE = 'EnergyPlus-MCP/energyplus-mcp-server/sample_files/USA_CA_San.Francisco.Intl.AP.724940_TMY3.epw';

// Test IDFs in order of complexity
const TEST_IDFS = [
  { name: '1ZoneUncontrolled', path: 'nrel_testfiles/1ZoneUncontrolled.idf' },
  { name: '1ZoneEvapCooler', path: 'EnergyPlus-MCP/energyplus-mcp-server/sample_files/1ZoneEvapCooler.idf' },
  { name: '5ZoneAirCooled', path: 'nrel_testfiles/5ZoneAirCooled.idf' },
  { name: '5ZoneAirCooled (sample)', path: 'EnergyPlus-MCP/energyplus-mcp-server/sample_files/5ZoneAirCooled.idf' },
  { name: 'RefBldgLargeOffice (483KB)', path: 'nrel_testfiles/RefBldgLargeOfficeNew2004_Chicago.idf' },
];

/**
 * Read files
 */
function readFiles(idfPath) {
  try {
    const idfFullPath = join(process.cwd(), idfPath);
    const weatherPath = join(process.cwd(), WEATHER_FILE);
    
    const idfContent = readFileSync(idfFullPath, 'utf-8');
    const weatherContent = readFileSync(weatherPath, 'utf-8');
    
    return { idfContent, weatherContent, idfSize: idfContent.length };
  } catch (error) {
    throw new Error(`Error reading files: ${error.message}`);
  }
}

/**
 * Run simulation
 */
async function runSimulation(idfContent, weatherContent, testName) {
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
      return { success: false, elapsed, error: `HTTP ${response.status}: ${errorText.substring(0, 200)}` };
    }

    const results = await response.json();
    
    if (results.simulation_status === 'error') {
      return { success: false, elapsed, error: results.error_message || 'Simulation failed' };
    }

    return { 
      success: true, 
      elapsed, 
      results: {
        totalEnergy: results.total_energy_consumption ? `${(results.total_energy_consumption / 1000).toFixed(2)} kWh` : 'N/A',
        buildingArea: results.building_area || 'N/A',
        zones: results.zones_count || 'N/A'
      }
    };

  } catch (error) {
    return { success: false, elapsed: 'N/A', error: error.message };
  }
}

/**
 * Main execution
 */
async function main() {
  console.log('🚀 Testing Multiple IDF Files');
  console.log('=' .repeat(60));
  
  const results = [];
  
  for (const test of TEST_IDFS) {
    console.log(`\n📋 Testing: ${test.name}`);
    console.log(`   File: ${test.path}`);
    
    try {
      const { idfContent, weatherContent, idfSize } = readFiles(test.path);
      const idfSizeKB = (idfSize / 1024).toFixed(1);
      console.log(`   IDF Size: ${idfSizeKB} KB`);
      
      console.log(`   ⚡ Running simulation...`);
      const result = await runSimulation(idfContent, weatherContent, test.name);
      
      if (result.success) {
        console.log(`   ✅ SUCCESS in ${result.elapsed}s`);
        console.log(`      Total Energy: ${result.results.totalEnergy}`);
        console.log(`      Building Area: ${result.results.buildingArea} m²`);
        console.log(`      Zones: ${result.results.zones}`);
      } else {
        console.log(`   ❌ FAILED in ${result.elapsed}s`);
        console.log(`      Error: ${result.error}`);
      }
      
      results.push({
        name: test.name,
        sizeKB: idfSizeKB,
        ...result
      });
      
    } catch (error) {
      console.log(`   ❌ ERROR: ${error.message}`);
      results.push({
        name: test.name,
        sizeKB: 'N/A',
        success: false,
        error: error.message
      });
    }
    
    // Wait a bit between tests
    await new Promise(resolve => setTimeout(resolve, 2000));
  }
  
  console.log('\n📊 Summary');
  console.log('=' .repeat(60));
  console.log('IDF File'.padEnd(30) + 'Size'.padEnd(10) + 'Status'.padEnd(10) + 'Time'.padEnd(10));
  console.log('-'.repeat(60));
  
  for (const r of results) {
    const status = r.success ? '✅ PASS' : '❌ FAIL';
    const time = r.elapsed ? `${r.elapsed}s` : 'N/A';
    const size = r.sizeKB ? `${r.sizeKB} KB` : 'N/A';
    console.log(r.name.padEnd(30) + size.padEnd(10) + status.padEnd(10) + time.padEnd(10));
  }
  
  console.log('\n✅ Test Complete!');
}

main();


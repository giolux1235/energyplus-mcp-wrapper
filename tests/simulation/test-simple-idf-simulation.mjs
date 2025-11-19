#!/usr/bin/env node
/**
 * Test with Simple IDF File
 * Uses a simple test IDF file instead of IDF Creator output
 */

import { readFileSync } from 'fs';
import { join } from 'path';

// Configuration
const ENERGYPLUS_API_URL = 'https://web-production-1d1be.up.railway.app/simulate';

// Simple IDF file
const SIMPLE_IDF = 'nrel_testfiles/1ZoneUncontrolled.idf';
const WEATHER_FILE = 'EnergyPlus-MCP/energyplus-mcp-server/sample_files/USA_CA_San.Francisco.Intl.AP.724940_TMY3.epw';

/**
 * Read files
 */
function readFiles() {
  try {
    const idfPath = join(process.cwd(), SIMPLE_IDF);
    const weatherPath = join(process.cwd(), WEATHER_FILE);
    
    console.log(`📁 Reading IDF: ${idfPath}`);
    const idfContent = readFileSync(idfPath, 'utf-8');
    console.log(`   ✅ IDF loaded: ${idfContent.length} bytes`);
    
    console.log(`📁 Reading Weather: ${weatherPath}`);
    const weatherContent = readFileSync(weatherPath, 'utf-8');
    console.log(`   ✅ Weather loaded: ${weatherContent.length} bytes`);
    
    return { idfContent, weatherContent };
  } catch (error) {
    console.error(`❌ Error reading files: ${error.message}`);
    throw error;
  }
}

/**
 * Run EnergyPlus simulation
 */
async function runSimulation(idfContent, weatherContent) {
  console.log('\n⚡ Running EnergyPlus Simulation with Simple IDF');
  console.log('=' .repeat(60));
  console.log(`   IDF size: ${idfContent.length} bytes`);
  console.log(`   Weather size: ${weatherContent.length} bytes`);
  
  try {
    const requestBody = {
      idf_content: idfContent,
      weather_content: weatherContent
    };

    console.log(`\n📤 Sending simulation request to: ${ENERGYPLUS_API_URL}`);
    
    const startTime = Date.now();
    const response = await fetch(ENERGYPLUS_API_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(requestBody)
    });

    const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
    console.log(`   ⏱️  Response received in ${elapsed}s`);

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`EnergyPlus API error (${response.status}): ${errorText}`);
    }

    const results = await response.json();
    console.log(`   ✅ Simulation completed successfully`);
    
    return results;

  } catch (error) {
    console.error(`   ❌ Error running simulation: ${error.message}`);
    throw error;
  }
}

/**
 * Display results
 */
function displayResults(results) {
  console.log('\n📊 Simulation Results');
  console.log('=' .repeat(60));

  if (results.simulation_status === 'error') {
    console.log('❌ Simulation Error:');
    console.log(`   ${results.error_message || 'Unknown error'}`);
    return;
  }

  console.log('✅ Simulation Status: SUCCESS');
  console.log(`\n📈 Energy Consumption:`);
  
  if (results.total_energy_consumption !== undefined) {
    const totalKwh = (results.total_energy_consumption / 1000).toLocaleString();
    console.log(`   Total Energy: ${totalKwh} kWh`);
  }

  if (results.heating_energy !== undefined && results.heating_energy !== 0) {
    console.log(`   Heating: ${(results.heating_energy / 1000).toLocaleString()} kWh`);
  }

  if (results.cooling_energy !== undefined && results.cooling_energy !== 0) {
    console.log(`   Cooling: ${(results.cooling_energy / 1000).toLocaleString()} kWh`);
  }

  if (results.lighting_energy !== undefined && results.lighting_energy !== 0) {
    console.log(`   Lighting: ${(results.lighting_energy / 1000).toLocaleString()} kWh`);
  }

  if (results.building_area) {
    console.log(`\n🏢 Building Area: ${results.building_area.toLocaleString()} m²`);
  }

  if (results.zones_count) {
    console.log(`   Zones: ${results.zones_count}`);
  }

  console.log(`\n📋 Full Results Structure:`);
  console.log(`   Available fields: ${Object.keys(results).join(', ')}`);
}

/**
 * Main execution
 */
async function main() {
  console.log('🚀 Simple IDF Simulation Test');
  console.log('=' .repeat(60));
  
  try {
    // Read simple IDF and weather files
    const { idfContent, weatherContent } = readFiles();

    // Run simulation
    const results = await runSimulation(idfContent, weatherContent);

    // Display results
    displayResults(results);

    console.log('\n✅ Test Complete!');
    console.log('=' .repeat(60));

  } catch (error) {
    console.error('\n❌ Test Failed!');
    console.error('=' .repeat(60));
    console.error(`Error: ${error.message}`);
    process.exit(1);
  }
}

// Run the test
main();



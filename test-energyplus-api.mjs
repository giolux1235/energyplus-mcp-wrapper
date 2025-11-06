#!/usr/bin/env node
/**
 * Test EnergyPlus API with Example Files
 * Tests the API with IDF and weather files from the repository
 */

import { readFileSync, writeFileSync } from 'fs';
import { join } from 'path';

// Configuration
const ENERGYPLUS_API_URL = 'https://web-production-1d1be.up.railway.app/simulate';

// Test files - using simple 1-zone building
const IDF_FILE = 'EnergyPlus-MCP/energyplus-mcp-server/sample_files/1ZoneUncontrolled.idf';
const WEATHER_FILE = 'EnergyPlus-MCP/energyplus-mcp-server/sample_files/USA_CA_San.Francisco.Intl.AP.724940_TMY3.epw';

/**
 * Read files
 */
function readFiles() {
  try {
    const idfPath = join(process.cwd(), IDF_FILE);
    const weatherPath = join(process.cwd(), WEATHER_FILE);
    
    console.log(`📁 Reading IDF: ${idfPath}`);
    if (!readFileSync(idfPath, { encoding: 'utf-8', flag: 'r' })) {
      throw new Error(`IDF file not found: ${idfPath}`);
    }
    const idfContent = readFileSync(idfPath, 'utf-8');
    console.log(`   ✅ IDF loaded: ${idfContent.length.toLocaleString()} bytes`);
    console.log(`   📄 First 200 chars: ${idfContent.substring(0, 200).replace(/\n/g, ' ')}...`);
    
    console.log(`\n📁 Reading Weather: ${weatherPath}`);
    if (!readFileSync(weatherPath, { encoding: 'utf-8', flag: 'r' })) {
      throw new Error(`Weather file not found: ${weatherPath}`);
    }
    const weatherContent = readFileSync(weatherPath, 'utf-8');
    console.log(`   ✅ Weather loaded: ${weatherContent.length.toLocaleString()} bytes`);
    console.log(`   📄 First 200 chars: ${weatherContent.substring(0, 200).replace(/\n/g, ' ')}...`);
    
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
  console.log('\n⚡ Running EnergyPlus Simulation');
  console.log('='.repeat(60));
  console.log(`   IDF size: ${idfContent.length.toLocaleString()} bytes`);
  console.log(`   Weather size: ${weatherContent.length.toLocaleString()} bytes`);
  console.log(`   API URL: ${ENERGYPLUS_API_URL}`);
  
  try {
    const requestBody = {
      idf_content: idfContent,
      weather_content: weatherContent
    };

    console.log(`\n📤 Sending simulation request...`);
    console.log(`   Request body size: ${JSON.stringify(requestBody).length.toLocaleString()} bytes`);
    
    const startTime = Date.now();
    const response = await fetch(ENERGYPLUS_API_URL, {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json',
        'Accept': 'application/json'
      },
      body: JSON.stringify(requestBody)
    });

    const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
    console.log(`   ⏱️  Response received in ${elapsed}s`);
    console.log(`   📊 Status: ${response.status} ${response.statusText}`);

    if (!response.ok) {
      const errorText = await response.text();
      console.error(`   ❌ Error response: ${errorText.substring(0, 500)}`);
      throw new Error(`EnergyPlus API error (${response.status}): ${errorText.substring(0, 200)}`);
    }

    const results = await response.json();
    console.log(`   ✅ Simulation completed successfully`);
    
    return results;

  } catch (error) {
    console.error(`   ❌ Error running simulation: ${error.message}`);
    if (error.cause) {
      console.error(`   Cause: ${error.cause}`);
    }
    throw error;
  }
}

/**
 * Display results in a formatted way
 */
function displayResults(results) {
  console.log('\n📊 Simulation Results');
  console.log('='.repeat(60));

  if (results.simulation_status === 'error') {
    console.log('❌ Simulation Error:');
    console.log(`   ${results.error_message || 'Unknown error'}`);
    if (results.warnings && results.warnings.length > 0) {
      console.log(`\n⚠️  Warnings (${results.warnings.length}):`);
      results.warnings.slice(0, 5).forEach((w, i) => {
        console.log(`   ${i + 1}. ${w.substring(0, 100)}`);
      });
    }
    return;
  }

  console.log('✅ Simulation Status: SUCCESS');
  console.log(`\n📈 Energy Consumption:`);
  
  if (results.total_energy_consumption !== undefined) {
    const totalKwh = results.total_energy_consumption;
    console.log(`   Total Energy: ${totalKwh.toLocaleString(undefined, { maximumFractionDigits: 2 })} kWh`);
  }

  if (results.electricity_kwh !== undefined && results.electricity_kwh !== 0) {
    console.log(`   Electricity: ${results.electricity_kwh.toLocaleString(undefined, { maximumFractionDigits: 2 })} kWh`);
  }

  if (results.gas_kwh !== undefined && results.gas_kwh !== 0) {
    console.log(`   Natural Gas: ${results.gas_kwh.toLocaleString(undefined, { maximumFractionDigits: 2 })} kWh`);
  }

  if (results.heating_energy !== undefined && results.heating_energy !== 0) {
    console.log(`   Heating: ${results.heating_energy.toLocaleString(undefined, { maximumFractionDigits: 2 })} kWh`);
  }

  if (results.cooling_energy !== undefined && results.cooling_energy !== 0) {
    console.log(`   Cooling: ${results.cooling_energy.toLocaleString(undefined, { maximumFractionDigits: 2 })} kWh`);
  }

  if (results.lighting_energy !== undefined && results.lighting_energy !== 0) {
    console.log(`   Lighting: ${results.lighting_energy.toLocaleString(undefined, { maximumFractionDigits: 2 })} kWh`);
  }

  if (results.equipment_energy !== undefined && results.equipment_energy !== 0) {
    console.log(`   Equipment: ${results.equipment_energy.toLocaleString(undefined, { maximumFractionDigits: 2 })} kWh`);
  }

  if (results.fans_energy !== undefined && results.fans_energy !== 0) {
    console.log(`   Fans: ${results.fans_energy.toLocaleString(undefined, { maximumFractionDigits: 2 })} kWh`);
  }

  if (results.pumps_energy !== undefined && results.pumps_energy !== 0) {
    console.log(`   Pumps: ${results.pumps_energy.toLocaleString(undefined, { maximumFractionDigits: 2 })} kWh`);
  }

  console.log(`\n🏢 Building Metrics:`);
  
  if (results.building_area) {
    console.log(`   Building Area: ${results.building_area.toLocaleString(undefined, { maximumFractionDigits: 2 })} m²`);
  }

  if (results.zones_count) {
    console.log(`   Zones: ${results.zones_count}`);
  }

  if (results.energy_intensity) {
    console.log(`   Energy Use Intensity (EUI): ${results.energy_intensity.toLocaleString(undefined, { maximumFractionDigits: 2 })} kWh/m²`);
  }

  if (results.peak_demand) {
    console.log(`   Peak Demand: ${results.peak_demand.toLocaleString(undefined, { maximumFractionDigits: 2 })} kW`);
  }

  if (results.energy_results) {
    console.log(`\n📋 Energy Results (Structured):`);
    console.log(`   Total Site Energy: ${results.energy_results.total_site_energy_kwh?.toLocaleString(undefined, { maximumFractionDigits: 2 })} kWh`);
    console.log(`   Building Area: ${results.energy_results.building_area_m2?.toLocaleString(undefined, { maximumFractionDigits: 2 })} m²`);
    console.log(`   EUI: ${results.energy_results.eui_kwh_m2?.toLocaleString(undefined, { maximumFractionDigits: 2 })} kWh/m²`);
    console.log(`   Extraction Method: ${results.energy_results.extraction_method || 'unknown'}`);
  }

  console.log(`\n📊 Metadata:`);
  console.log(`   Version: ${results.version || 'unknown'}`);
  console.log(`   EnergyPlus Version: ${results.energyplus_version || 'unknown'}`);
  console.log(`   Real Simulation: ${results.real_simulation ? 'Yes' : 'No'}`);
  console.log(`   Exit Code: ${results.exit_code || 'unknown'}`);
  console.log(`   Warnings Count: ${results.warnings_count || 0}`);
  
  if (results.warnings && results.warnings.length > 0) {
    console.log(`\n⚠️  Warnings (showing first 3):`);
    results.warnings.slice(0, 3).forEach((w, i) => {
      console.log(`   ${i + 1}. ${w.substring(0, 150)}`);
    });
  }

  if (results.output_files && results.output_files.length > 0) {
    console.log(`\n📁 Output Files Generated:`);
    results.output_files.forEach(file => {
      console.log(`   - ${file}`);
    });
  }

  console.log(`\n📋 All Available Fields:`);
  console.log(`   ${Object.keys(results).join(', ')}`);
}

/**
 * Save results to file
 */
function saveResults(results, filename = 'test-results.json') {
  try {
    writeFileSync(filename, JSON.stringify(results, null, 2));
    console.log(`\n💾 Results saved to: ${filename}`);
  } catch (error) {
    console.warn(`⚠️  Could not save results: ${error.message}`);
  }
}

/**
 * Main execution
 */
async function main() {
  console.log('🚀 EnergyPlus API Test');
  console.log('='.repeat(60));
  console.log(`   IDF File: ${IDF_FILE}`);
  console.log(`   Weather File: ${WEATHER_FILE}`);
  console.log(`   API URL: ${ENERGYPLUS_API_URL}`);
  console.log('='.repeat(60));
  
  try {
    // Read files
    const { idfContent, weatherContent } = readFiles();

    // Run simulation
    const results = await runSimulation(idfContent, weatherContent);

    // Display results
    displayResults(results);

    // Save results
    saveResults(results, 'test-results.json');

    console.log('\n✅ Test Complete!');
    console.log('='.repeat(60));

  } catch (error) {
    console.error('\n❌ Test Failed!');
    console.error('='.repeat(60));
    console.error(`Error: ${error.message}`);
    if (error.stack) {
      console.error(`\nStack trace:\n${error.stack}`);
    }
    process.exit(1);
  }
}

// Run the test
main();


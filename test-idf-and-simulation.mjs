#!/usr/bin/env node
/**
 * Test Script: Generate IDF from Creator Service and Run EnergyPlus Simulation
 * 
 * This script:
 * 1. Generates an IDF file using the IDF Creator service with a random address
 * 2. Uses a local weather file
 * 3. Runs an EnergyPlus simulation using the EnergyPlus service
 * 4. Displays the results
 */

import { readFileSync } from 'fs';
import { join } from 'path';

// Configuration
const IDF_CREATOR_API_URL = 'https://web-production-3092c.up.railway.app';
const ENERGYPLUS_API_URL = 'https://web-production-1d1be.up.railway.app/simulate';

// Random addresses for testing
const RANDOM_ADDRESSES = [
  '1600 Pennsylvania Avenue NW, Washington, DC 20500',
  '350 5th Ave, New York, NY 10118',
  '123 Main St, Los Angeles, CA 90001',
  '456 Oak Avenue, Denver, CO 80202',
  '789 Pine Street, Seattle, WA 98101',
  '321 Elm Drive, Boston, MA 02108',
  '654 Maple Lane, Austin, TX 78701',
  '987 Birch Road, Miami, FL 33101'
];

// Available weather files (tried in order - prefer larger files first)
const WEATHER_FILES = [
  'EnergyPlus-MCP/energyplus-mcp-server/sample_files/USA_CA_San.Francisco.Intl.AP.724940_TMY3.epw',
  'EnergyPlus-MCP/energyplus-mcp-server/illustrative examples/USA_IL_Chicago-OHare.Intl.AP.725300_TMY3.epw',
  'speed-build-engine/USA_IL_Chicago-OHare.Intl.AP.725300_TMY3.epw'
];

/**
 * Find available weather file
 */
function findWeatherFile() {
  for (const filePath of WEATHER_FILES) {
    try {
      const fullPath = join(process.cwd(), filePath);
      readFileSync(fullPath, 'utf-8');
      return filePath;
    } catch (error) {
      // Try next file
      continue;
    }
  }
  throw new Error('No weather file found. Tried: ' + WEATHER_FILES.join(', '));
}

/**
 * Get a random address
 */
function getRandomAddress() {
  return RANDOM_ADDRESSES[Math.floor(Math.random() * RANDOM_ADDRESSES.length)];
}

/**
 * Read weather file from local machine
 */
function readWeatherFile(filePath) {
  try {
    const fullPath = join(process.cwd(), filePath);
    console.log(`📁 Reading weather file: ${fullPath}`);
    const content = readFileSync(fullPath, 'utf-8');
    console.log(`   ✅ Weather file loaded: ${content.length} bytes`);
    return content;
  } catch (error) {
    console.error(`   ❌ Error reading weather file: ${error.message}`);
    throw error;
  }
}

/**
 * Generate IDF using IDF Creator service
 */
async function generateIDF(address, buildingType = 'office', floorArea = 5000, numFloors = 5) {
  console.log('\n🏗️  Step 1: Generating IDF from Creator Service');
  console.log('=' .repeat(60));
  console.log(`📍 Address: ${address}`);
  console.log(`🏢 Building Type: ${buildingType}`);
  console.log(`📐 Floor Area: ${floorArea} m²`);
  console.log(`🏢 Number of Floors: ${numFloors}`);
  
  try {
    console.log(`\n📤 Calling IDF Creator API: ${IDF_CREATOR_API_URL}/generate`);
    
    const response = await fetch(`${IDF_CREATOR_API_URL}/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        address: address,
        building_type: buildingType,
        floor_area: floorArea,
        num_floors: numFloors
      })
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`IDF Creator API returned ${response.status}: ${errorText}`);
    }

    const data = await response.json();
    console.log(`   ✅ Response received: ${JSON.stringify(Object.keys(data)).slice(0, 100)}...`);

    if (!data.success) {
      throw new Error('IDF Creator did not return success: ' + JSON.stringify(data));
    }

    // Get IDF content
    let idfContent;
    if (data.download_url) {
      const downloadUrl = `${IDF_CREATOR_API_URL}${data.download_url}`;
      console.log(`   📥 Downloading IDF from: ${downloadUrl}`);
      const idfResponse = await fetch(downloadUrl);
      
      if (!idfResponse.ok) {
        throw new Error(`Failed to download IDF file: ${idfResponse.status}`);
      }
      
      idfContent = await idfResponse.text();
      console.log(`   ✅ IDF downloaded: ${idfContent.length} bytes`);
    } else if (data.idf_content) {
      idfContent = data.idf_content;
      console.log(`   ✅ IDF content received: ${idfContent.length} bytes`);
    } else {
      throw new Error('IDF Creator did not return IDF content or download URL');
    }

    // Show IDF preview
    const preview = idfContent.substring(0, 300).replace(/\n/g, ' ').substring(0, 200);
    console.log(`   📄 IDF Preview: ${preview}...`);

    return {
      success: true,
      idf_content: idfContent,
      parameters: data.parameters_used || data.parameters || {}
    };

  } catch (error) {
    console.error(`   ❌ Error generating IDF: ${error.message}`);
    throw error;
  }
}

/**
 * Run EnergyPlus simulation with retry logic
 */
async function runSimulation(idfContent, weatherContent, maxRetries = 2) {
  console.log('\n⚡ Step 2: Running EnergyPlus Simulation');
  console.log('=' .repeat(60));
  console.log(`   IDF size: ${idfContent.length} bytes`);
  console.log(`   Weather size: ${weatherContent.length} bytes`);
  
  const requestBody = {
    idf_content: idfContent,
    weather_content: weatherContent
  };

  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      console.log(`\n📤 Attempt ${attempt}/${maxRetries}: Sending simulation request to: ${ENERGYPLUS_API_URL}`);
      console.log(`   Request body size: ${JSON.stringify(requestBody).length} bytes`);
      
      const startTime = Date.now();
      
      // Use AbortController for timeout
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 300000); // 5 minute timeout
      
      const response = await fetch(ENERGYPLUS_API_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestBody),
        signal: controller.signal
      });

      clearTimeout(timeoutId);
      const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
      console.log(`   ⏱️  Response received in ${elapsed}s`);

      if (!response.ok) {
        const errorText = await response.text();
        console.log(`   ⚠️  Response status: ${response.status}`);
        
        // If it's a server error (5xx) and we have retries left, try again
        if (response.status >= 500 && response.status < 600 && attempt < maxRetries) {
          const waitTime = attempt * 5; // Wait 5s, 10s, etc.
          console.log(`   ⏳ Server error detected. Waiting ${waitTime}s before retry...`);
          await new Promise(resolve => setTimeout(resolve, waitTime * 1000));
          continue;
        }
        
        throw new Error(`EnergyPlus API error (${response.status}): ${errorText}`);
      }

      const results = await response.json();
      console.log(`   ✅ Simulation completed successfully`);
      
      return results;

    } catch (error) {
      if (error.name === 'AbortError') {
        console.error(`   ⏱️  Request timed out after 5 minutes`);
        if (attempt < maxRetries) {
          console.log(`   ⏳ Retrying...`);
          await new Promise(resolve => setTimeout(resolve, 10000));
          continue;
        }
        throw new Error('Simulation request timed out after 5 minutes');
      }
      
      if (attempt >= maxRetries) {
        console.error(`   ❌ Error running simulation: ${error.message}`);
        throw error;
      }
      
      // For network errors, retry
      if (error.message.includes('fetch') || error.message.includes('network')) {
        const waitTime = attempt * 5;
        console.log(`   ⚠️  Network error: ${error.message}`);
        console.log(`   ⏳ Waiting ${waitTime}s before retry...`);
        await new Promise(resolve => setTimeout(resolve, waitTime * 1000));
        continue;
      }
      
      throw error;
    }
  }
}

/**
 * Display simulation results
 */
function displayResults(results) {
  console.log('\n📊 Step 3: Simulation Results');
  console.log('=' .repeat(60));

  if (results.simulation_status === 'error') {
    console.log('❌ Simulation Error:');
    console.log(`   ${results.error_message || 'Unknown error'}`);
    if (results.errors && results.errors.length > 0) {
      console.log('\n   Errors:');
      results.errors.forEach((err, i) => {
        console.log(`   ${i + 1}. ${err}`);
      });
    }
    return;
  }

  console.log('✅ Simulation Status: SUCCESS');
  console.log(`\n📈 Energy Consumption Summary:`);
  
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

  if (results.equipment_energy !== undefined && results.equipment_energy !== 0) {
    console.log(`   Equipment: ${(results.equipment_energy / 1000).toLocaleString()} kWh`);
  }

  if (results.hvac_energy !== undefined && results.hvac_energy !== 0) {
    console.log(`   HVAC: ${(results.hvac_energy / 1000).toLocaleString()} kWh`);
  }

  if (results.peak_demand || results.peakDemand) {
    console.log(`\n⚡ Peak Demand: ${(results.peak_demand || results.peakDemand).toFixed(2)} kW`);
  }

  if (results.energy_intensity || results.energyIntensity) {
    const eui = results.energy_intensity || results.energyIntensity;
    console.log(`   Energy Use Intensity: ${eui.toLocaleString()} kWh/m²`);
  }

  if (results.building_area) {
    console.log(`\n🏢 Building Area: ${results.building_area.toLocaleString()} m²`);
  }

  if (results.zones_count) {
    console.log(`   Zones: ${results.zones_count}`);
  }

  if (results.building_type && results.building_type !== 'none') {
    console.log(`   Building Type: ${results.building_type}`);
  }

  // Show API metadata
  if (results.version || results.energyplus_version) {
    console.log(`\n🔧 Technical Details:`);
    if (results.energyplus_version) {
      console.log(`   EnergyPlus Version: ${results.energyplus_version}`);
    }
    if (results.version) {
      console.log(`   API Version: ${results.version}`);
    }
    if (results.real_simulation !== undefined) {
      console.log(`   Real Simulation: ${results.real_simulation ? 'Yes' : 'No'}`);
    }
    if (results.exit_code !== undefined) {
      console.log(`   Exit Code: ${results.exit_code}`);
    }
    if (results.warnings_count !== undefined) {
      console.log(`   Warnings: ${results.warnings_count}`);
    }
    if (results.processing_time !== undefined) {
      console.log(`   Processing Time: ${results.processing_time}s`);
    }
  }

  // Show recommendations if available
  if (results.recommendations && results.recommendations.length > 0) {
    console.log(`\n💡 Recommendations:`);
    results.recommendations.forEach((rec, i) => {
      console.log(`   ${i + 1}. ${rec}`);
    });
  }

  // Show full results structure
  console.log(`\n📋 Full Results Structure:`);
  console.log(`   Available fields: ${Object.keys(results).join(', ')}`);
}

/**
 * Main execution
 */
async function main() {
  console.log('🚀 IDF Creator + EnergyPlus Simulation Test');
  console.log('=' .repeat(60));
  
  let idfResult;
  let weatherFile;
  
  try {
    // Step 1: Generate IDF
    const randomAddress = getRandomAddress();
    idfResult = await generateIDF(randomAddress, 'office', 5000, 5);
    
    if (!idfResult.success) {
      throw new Error('Failed to generate IDF');
    }

    // Step 2: Read weather file (use first available)
    console.log('\n🌤️  Step 2: Loading Weather File');
    console.log('=' .repeat(60));
    weatherFile = findWeatherFile();
    const weatherContent = readWeatherFile(weatherFile);
    console.log(`   Weather file: ${weatherFile.split('/').pop()}`);

    // Step 3: Run simulation
    const simulationResults = await runSimulation(idfResult.idf_content, weatherContent);

    // Step 4: Display results
    displayResults(simulationResults);

    console.log('\n✅ Test Complete!');
    console.log('=' .repeat(60));
    
    // Show summary
    console.log('\n📋 Summary:');
    console.log(`   ✅ IDF Generated: ${(idfResult.idf_content.length / 1024).toFixed(1)} KB`);
    console.log(`   ✅ Weather File: ${weatherFile.split('/').pop()}`);
    if (simulationResults.simulation_status === 'error') {
      console.log(`   ⚠️  Simulation: Failed (EnergyPlus service returned error)`);
    } else {
      console.log(`   ✅ Simulation: Completed successfully`);
    }

  } catch (error) {
    console.error('\n❌ Test Failed!');
    console.error('=' .repeat(60));
    console.error(`Error: ${error.message}`);
    
    // Show what we accomplished
    if (typeof idfResult !== 'undefined' && idfResult.success) {
      console.log('\n📋 Partial Success:');
      console.log(`   ✅ IDF Generated: ${(idfResult.idf_content.length / 1024).toFixed(1)} KB`);
      console.log(`   ✅ IDF Parameters: ${JSON.stringify(idfResult.parameters || {})}`);
      console.log(`   ❌ Simulation: Failed - ${error.message}`);
      console.log('\n💡 Note: The IDF Creator service is working correctly.');
      console.log('   The EnergyPlus service may be experiencing issues or timeouts.');
    }
    
    if (error.stack) {
      console.error(`\nStack trace:\n${error.stack}`);
    }
    process.exit(1);
  }
}

// Run the test
main();


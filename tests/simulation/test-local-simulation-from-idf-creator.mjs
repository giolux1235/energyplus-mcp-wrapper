#!/usr/bin/env node
/**
 * Test Script: Generate IDF from Creator Service and Run EnergyPlus Simulation Locally
 * 
 * This script:
 * 1. Generates an IDF file using the IDF Creator service with a random Chicago address
 * 2. Uses the local Chicago weather file
 * 3. Runs an EnergyPlus simulation locally
 * 4. Extracts and displays the results
 */

import { readFileSync, writeFileSync, mkdirSync, existsSync, readdirSync } from 'fs';
import { join } from 'path';
import { exec } from 'child_process';
import { promisify } from 'util';

const execAsync = promisify(exec);

// Configuration
const IDF_CREATOR_API_URL = 'https://web-production-3092c.up.railway.app';
const ENERGYPLUS_EXE = '/usr/local/bin/energyplus';
const ENERGYPLUS_IDD = '/usr/local/bin/Energy+.idd';

// Random Chicago addresses (matching the Chicago weather file)
const CHICAGO_ADDRESSES = [
  '233 S Wacker Dr, Chicago, IL 60606',  // Willis Tower area
  '350 N Orleans St, Chicago, IL 60654',  // River North
  '500 N Michigan Ave, Chicago, IL 60611', // Magnificent Mile
  '200 W Adams St, Chicago, IL 60606',    // Loop
  '1 N Dearborn St, Chicago, IL 60602',   // Loop
  '875 N Michigan Ave, Chicago, IL 60611', // John Hancock area
  '150 N Riverside Plaza, Chicago, IL 60606', // West Loop
  '123 W Wacker Dr, Chicago, IL 60601'    // Loop
];

// Weather file paths (try in order - use valid EPW files)
const WEATHER_FILES = [
  'EnergyPlus-MCP/energyplus-mcp-server/illustrative examples/USA_IL_Chicago-OHare.Intl.AP.725300_TMY3.epw',
  'EnergyPlus-MCP/energyplus-mcp-server/sample_files/USA_CA_San.Francisco.Intl.AP.724940_TMY3.epw'
];

/**
 * Get a random Chicago address
 */
function getRandomAddress() {
  return CHICAGO_ADDRESSES[Math.floor(Math.random() * CHICAGO_ADDRESSES.length)];
}

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
      continue;
    }
  }
  throw new Error('No Chicago weather file found. Tried: ' + WEATHER_FILES.join(', '));
}

/**
 * Read weather file
 */
function readWeatherFile(filePath) {
  try {
    const fullPath = join(process.cwd(), filePath);
    console.log(`📁 Reading weather file: ${fullPath}`);
    const content = readFileSync(fullPath, 'utf-8');
    console.log(`   ✅ Weather file loaded: ${(content.length / 1024).toFixed(1)} KB`);
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
  console.log('='.repeat(60));
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
    console.log(`   ✅ Response received`);

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
      console.log(`   ✅ IDF downloaded: ${(idfContent.length / 1024).toFixed(1)} KB`);
    } else if (data.idf_content) {
      idfContent = data.idf_content;
      console.log(`   ✅ IDF content received: ${(idfContent.length / 1024).toFixed(1)} KB`);
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
 * Run EnergyPlus simulation locally
 */
async function runLocalSimulation(idfContent, weatherContent, outputDir) {
  console.log('\n⚡ Step 2: Running EnergyPlus Simulation Locally');
  console.log('='.repeat(60));
  console.log(`   IDF size: ${(idfContent.length / 1024).toFixed(1)} KB`);
  console.log(`   Weather size: ${(weatherContent.length / 1024).toFixed(1)} KB`);
  console.log(`   Output directory: ${outputDir}`);
  
  try {
    // Create output directory
    mkdirSync(outputDir, { recursive: true });
    
    // Write IDF file
    const idfPath = join(outputDir, 'input.idf');
    writeFileSync(idfPath, idfContent, 'utf-8');
    console.log(`   📄 IDF file written: ${idfPath}`);
    
    // Write weather file
    const weatherPath = join(outputDir, 'weather.epw');
    writeFileSync(weatherPath, weatherContent, 'utf-8');
    console.log(`   🌤️  Weather file written: ${weatherPath}`);
    
    // Ensure Output:SQLite is in IDF
    if (!idfContent.includes('Output:SQLite')) {
      console.log(`   ⚠️  Adding Output:SQLite to IDF...`);
      const updatedIdf = idfContent + "\n\nOutput:SQLite,\n    Simple;        !- Option Type\n";
      writeFileSync(idfPath, updatedIdf, 'utf-8');
      idfContent = updatedIdf;
      console.log(`   ✅ Output:SQLite added`);
    }
    
    // Build EnergyPlus command - use absolute paths and proper quoting
    const cmd = [
      ENERGYPLUS_EXE,
      '-w', `"${weatherPath}"`,
      '-d', `"${outputDir}"`,
      '-i', `"${ENERGYPLUS_IDD}"`,
      `"${idfPath}"`
    ].join(' ');
    
    console.log(`\n🔧 Running EnergyPlus command...`);
    console.log(`   Command: ${cmd}`);
    
    const startTime = Date.now();
    
    // Change to output directory to run EnergyPlus (it needs to be in the output dir)
    const originalCwd = process.cwd();
    process.chdir(outputDir);
    
    // Run EnergyPlus with timeout (10 minutes) - use relative paths from output dir
    const relativeIdfPath = 'input.idf';
    const relativeWeatherPath = 'weather.epw';
    const relativeOutputDir = '.';
    
    const cmdFromOutputDir = [
      ENERGYPLUS_EXE,
      '-w', relativeWeatherPath,
      '-d', relativeOutputDir,
      '-i', ENERGYPLUS_IDD,
      relativeIdfPath
    ].join(' ');
    
    let stdout, stderr;
    try {
      const result = await execAsync(cmdFromOutputDir, {
        timeout: 600000, // 10 minutes
        maxBuffer: 10 * 1024 * 1024 // 10MB buffer
      });
      stdout = result.stdout;
      stderr = result.stderr;
    } finally {
      // Restore original working directory
      process.chdir(originalCwd);
    }
    
    const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
    console.log(`   ⏱️  Simulation completed in ${elapsed}s`);
    
    if (stderr) {
      console.log(`   ⚠️  STDERR: ${stderr.substring(0, 500)}...`);
    }
    
    return {
      success: true,
      output_dir: outputDir,
      elapsed_time: elapsed,
      stdout: stdout.substring(0, 1000), // First 1000 chars
      stderr: stderr ? stderr.substring(0, 1000) : ''
    };
    
  } catch (error) {
    console.error(`   ❌ Error running simulation: ${error.message}`);
    if (error.stdout) {
      console.error(`   STDOUT: ${error.stdout.substring(0, 500)}`);
    }
    if (error.stderr) {
      console.error(`   STDERR: ${error.stderr.substring(0, 500)}`);
    }
    throw error;
  }
}

/**
 * Extract energy data from SQLite output
 */
async function extractEnergyData(outputDir) {
  console.log('\n📊 Step 3: Extracting Energy Data');
  console.log('='.repeat(60));
  
  try {
    // Try to use the local extraction script
    const extractScript = join(process.cwd(), 'extract-energy-local.py');
    
    if (existsSync(extractScript)) {
      console.log(`   📥 Using extract-energy-local.py...`);
      
      // Find SQLite file
      const files = readdirSync(outputDir);
      const sqliteFile = files.find(f => f.endsWith('.sql') || f.endsWith('.sqlite') || f.endsWith('.db'));
      
      if (sqliteFile) {
        const sqlitePath = join(outputDir, sqliteFile);
        console.log(`   📄 Found SQLite file: ${sqliteFile}`);
        
        try {
          const { stdout } = await execAsync(`python3 "${extractScript}" "${sqlitePath}" --period-days 365`);
          const results = JSON.parse(stdout);
          console.log(`   ✅ Energy data extracted`);
          return results;
        } catch (error) {
          console.log(`   ⚠️  Extraction script failed: ${error.message}`);
          console.log(`   ⚠️  Trying manual extraction...`);
        }
      }
    }
    
    // Manual extraction - list output files
    const files = readdirSync(outputDir);
    console.log(`   📁 Output files: ${files.join(', ')}`);
    
    const sqliteFile = files.find(f => f.includes('eplusout') && (f.endsWith('.sql') || f.endsWith('.sqlite')));
    if (sqliteFile) {
      console.log(`   ✅ SQLite output file found: ${sqliteFile}`);
    }
    
    // Return basic info
    return {
      extraction_method: 'manual',
      output_files: files,
      sqlite_file: sqliteFile || null
    };
    
  } catch (error) {
    console.error(`   ⚠️  Error extracting energy data: ${error.message}`);
    return {
      extraction_method: 'failed',
      error: error.message
    };
  }
}

/**
 * Display results
 */
function displayResults(simulationResult, energyData) {
  console.log('\n📊 Step 4: Results Summary');
  console.log('='.repeat(60));
  
  console.log(`\n✅ Simulation Status: ${simulationResult.success ? 'SUCCESS' : 'FAILED'}`);
  console.log(`   Elapsed Time: ${simulationResult.elapsed_time}s`);
  console.log(`   Output Directory: ${simulationResult.output_dir}`);
  
  if (energyData && energyData.energy_data) {
    console.log(`\n📈 Energy Consumption Summary:`);
    const ed = energyData.energy_data;
    
    if (ed.total_energy_consumption !== undefined) {
      console.log(`   Total Energy: ${(ed.total_energy_consumption / 1000).toLocaleString()} kWh`);
    }
    if (ed.electricity_kwh !== undefined) {
      console.log(`   Electricity: ${(ed.electricity_kwh / 1000).toLocaleString()} kWh`);
    }
    if (ed.gas_kwh !== undefined) {
      console.log(`   Natural Gas: ${(ed.gas_kwh / 1000).toLocaleString()} kWh`);
    }
    if (ed.heating_energy !== undefined && ed.heating_energy > 0) {
      console.log(`   Heating: ${(ed.heating_energy / 1000).toLocaleString()} kWh`);
    }
    if (ed.cooling_energy !== undefined && ed.cooling_energy > 0) {
      console.log(`   Cooling: ${(ed.cooling_energy / 1000).toLocaleString()} kWh`);
    }
    if (ed.lighting_energy !== undefined && ed.lighting_energy > 0) {
      console.log(`   Lighting: ${(ed.lighting_energy / 1000).toLocaleString()} kWh`);
    }
    if (ed.equipment_energy !== undefined && ed.equipment_energy > 0) {
      console.log(`   Equipment: ${(ed.equipment_energy / 1000).toLocaleString()} kWh`);
    }
    if (ed.building_area && ed.building_area > 0) {
      console.log(`\n🏢 Building Area: ${ed.building_area.toLocaleString()} m²`);
      if (ed.total_energy_consumption) {
        const eui = (ed.total_energy_consumption / ed.building_area).toFixed(2);
        console.log(`   Energy Use Intensity (EUI): ${eui} kWh/m²`);
      }
    }
  } else if (energyData && energyData.output_files) {
    console.log(`\n📁 Output Files Generated:`);
    energyData.output_files.forEach(file => {
      console.log(`   - ${file}`);
    });
  }
  
  console.log(`\n✅ Test Complete!`);
  console.log(`   Output directory: ${simulationResult.output_dir}`);
  console.log(`   You can examine the output files for detailed results.`);
}

/**
 * Main execution
 */
async function main() {
  console.log('🚀 IDF Creator + Local EnergyPlus Simulation Test');
  console.log('='.repeat(60));
  
  let idfResult;
  let weatherFile;
  let outputDir;
  
  try {
    // Step 1: Generate IDF
    const randomAddress = getRandomAddress();
    idfResult = await generateIDF(randomAddress, 'office', 5000, 5);
    
    if (!idfResult.success) {
      throw new Error('Failed to generate IDF');
    }

    // Step 2: Read weather file
    console.log('\n🌤️  Loading Weather File');
    console.log('='.repeat(60));
    weatherFile = findWeatherFile();
    const weatherContent = readWeatherFile(weatherFile);
    console.log(`   Weather file: ${weatherFile.split('/').pop()}`);

    // Step 3: Run simulation locally
    outputDir = join(process.cwd(), 'local_simulation_output', `run_${Date.now()}`);
    const simulationResult = await runLocalSimulation(idfResult.idf_content, weatherContent, outputDir);

    // Step 4: Extract energy data
    const energyData = await extractEnergyData(outputDir);

    // Step 5: Display results
    displayResults(simulationResult, energyData);

  } catch (error) {
    console.error('\n❌ Test Failed!');
    console.error('='.repeat(60));
    console.error(`Error: ${error.message}`);
    
    if (typeof idfResult !== 'undefined' && idfResult.success) {
      console.log('\n📋 Partial Success:');
      console.log(`   ✅ IDF Generated: ${(idfResult.idf_content.length / 1024).toFixed(1)} KB`);
      console.log(`   ✅ IDF Parameters: ${JSON.stringify(idfResult.parameters || {})}`);
    }
    
    if (error.stack) {
      console.error(`\nStack trace:\n${error.stack}`);
    }
    process.exit(1);
  }
}

// Run the test
main();


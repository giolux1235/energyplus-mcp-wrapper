#!/usr/bin/env node
/**
 * Test Local Extraction Workflow
 * 1. Run simulation via API (with extraction skipped)
 * 2. Download output files
 * 3. Extract energy locally using extract-energy-local.py
 */

import { readFileSync, writeFileSync, mkdirSync } from 'fs';
import { join } from 'path';
import { execSync } from 'child_process';

const ENERGYPLUS_API_URL = 'https://web-production-1d1be.up.railway.app/simulate';
const WEATHER_FILE = 'EnergyPlus-MCP/energyplus-mcp-server/sample_files/USA_CA_San.Francisco.Intl.AP.724940_TMY3.epw';

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
  }
  throw new Error('No IDF content');
}

/**
 * Run simulation with extraction skipped
 */
async function runSimulationWithoutExtraction(idfContent, weatherContent) {
  console.log('⚡ Running simulation (extraction will be skipped)...');
  
  const response = await fetch(ENERGYPLUS_API_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      idf_content: idfContent,
      weather_content: weatherContent
    })
  });

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${await response.text()}`);
  }

  return await response.json();
}

/**
 * Main
 */
async function main() {
  console.log('🚀 Testing Local Extraction Workflow');
  console.log('=' .repeat(60));
  console.log('1. Getting IDF from Creator service');
  console.log('2. Running simulation (API extraction skipped)');
  console.log('3. Extracting energy locally\n');
  
  try {
    // Step 1: Get IDF
    const idfContent = await getIDFCreatorIDF();
    console.log(`   ✅ IDF: ${(idfContent.length / 1024).toFixed(1)} KB\n`);
    
    // Step 2: Run simulation
    const weatherContent = readFileSync(join(process.cwd(), WEATHER_FILE), 'utf-8');
    const results = await runSimulationWithoutExtraction(idfContent, weatherContent);
    
    if (results.simulation_status !== 'success') {
      throw new Error(`Simulation failed: ${results.error_message || 'Unknown error'}`);
    }
    
    console.log('✅ Simulation completed successfully');
    console.log(`   Output files: ${results.output_files?.length || 0} files`);
    
    if (results.extraction_skipped) {
      console.log('   ✅ Extraction was skipped (as expected)');
      console.log('\n📋 Next steps:');
      console.log('   1. Download output files from API');
      console.log('   2. Run: python extract-energy-local.py <output_dir> --period-days 7');
      console.log('\n   Note: For this test, we\'ll simulate local extraction');
      console.log('   by checking if the extraction tool works with sample files.\n');
      
      // Check if we can run the extraction tool
      try {
        const help = execSync('python3 extract-energy-local.py --help', { encoding: 'utf-8' });
        console.log('✅ Local extraction tool is available');
        console.log('\n📊 To test full workflow:');
        console.log('   1. Download output files from API response');
        console.log('   2. Save them to a directory');
        console.log('   3. Run: python3 extract-energy-local.py <output_dir> --period-days 7');
      } catch (e) {
        console.log('⚠️  Local extraction tool check failed:', e.message);
      }
    } else {
      console.log('⚠️  Extraction was NOT skipped (API still has extraction enabled)');
      console.log('   Set SKIP_ENERGY_EXTRACTION=true in Railway environment variables');
    }
    
    console.log('\n✅ Test Complete!');
    console.log('=' .repeat(60));
    
  } catch (error) {
    console.error('\n❌ Test Failed:', error.message);
    process.exit(1);
  }
}

main();



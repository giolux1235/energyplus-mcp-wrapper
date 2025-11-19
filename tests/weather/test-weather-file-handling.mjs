#!/usr/bin/env node
/**
 * Test script to verify weather file handling in EnergyPlus API simulation
 * Checks:
 * 1. Weather file is properly sent to API
 * 2. Weather file is correctly written and used by EnergyPlus
 * 3. Empty/missing weather file handling
 * 4. Weather file format validation
 */

import { readFileSync, existsSync } from 'fs';
import { join } from 'path';

const ENERGYPLUS_API_URL = process.env.ENERGYPLUS_API_URL || 'https://web-production-1d1be.up.railway.app/simulate';

// Test cases
const testCases = [
  {
    name: 'Valid weather file',
    description: 'Test with a valid EPW weather file',
    shouldPass: true
  },
  {
    name: 'Empty weather content',
    description: 'Test with empty weather_content string',
    shouldPass: false
  },
  {
    name: 'Missing weather_content field',
    description: 'Test without weather_content in request',
    shouldPass: false
  },
  {
    name: 'Invalid weather file format',
    description: 'Test with invalid weather file content',
    shouldPass: false
  }
];

// Find a test IDF file
function findTestIDF() {
  const possiblePaths = [
    'EnergyPlus-MCP/energyplus-mcp-server/sample_files/1ZoneUncontrolled.idf',
    'ashrae901_examples/ASHRAE901_OfficeSmall_Denver.idf',
    'sample_files/1ZoneUncontrolled.idf'
  ];
  
  for (const path of possiblePaths) {
    const fullPath = join(process.cwd(), path);
    if (existsSync(fullPath)) {
      return fullPath;
    }
  }
  
  throw new Error('No test IDF file found');
}

// Find a test weather file
function findTestWeather() {
  const possiblePaths = [
    'EnergyPlus-MCP/energyplus-mcp-server/sample_files/USA_CA_San.Francisco.Intl.AP.724940_TMY3.epw',
    'ashrae901_weather/USA_CO_Denver-Aurora-Buckley.AFB.724695_TMY3.epw',
    'sample_files/USA_CA_San.Francisco.Intl.AP.724940_TMY3.epw'
  ];
  
  for (const path of possiblePaths) {
    const fullPath = join(process.cwd(), path);
    if (existsSync(fullPath)) {
      return fullPath;
    }
  }
  
  throw new Error('No test weather file found');
}

// Validate EPW file format
function validateEPWFormat(content) {
  if (!content || content.trim().length === 0) {
    return { valid: false, error: 'Weather file is empty' };
  }
  
  const lines = content.split(/\r?\n/);
  
  // EPW files should start with LOCATION line
  if (lines.length === 0) {
    return { valid: false, error: 'Weather file has no content' };
  }
  
  const firstLine = lines[0].trim();
  if (!firstLine.toUpperCase().startsWith('LOCATION,')) {
    return { valid: false, error: 'Weather file does not start with LOCATION line' };
  }
  
  // Check for WEATHER DATA header
  let hasWeatherData = false;
  for (let i = 0; i < Math.min(20, lines.length); i++) {
    if (lines[i].toUpperCase().includes('DATA PERIODS')) {
      hasWeatherData = true;
      break;
    }
  }
  
  if (!hasWeatherData && lines.length < 10) {
    return { valid: false, error: 'Weather file appears incomplete (no DATA PERIODS found)' };
  }
  
  return { valid: true };
}

async function runTest(testCase, idfContent, weatherContent) {
  console.log(`\n${'='.repeat(70)}`);
  console.log(`Test: ${testCase.name}`);
  console.log(`Description: ${testCase.description}`);
  console.log('='.repeat(70));
  
  let requestBody;
  
  switch (testCase.name) {
    case 'Valid weather file':
      requestBody = {
        idf_content: idfContent,
        weather_content: weatherContent
      };
      break;
      
    case 'Empty weather content':
      requestBody = {
        idf_content: idfContent,
        weather_content: ''
      };
      break;
      
    case 'Missing weather_content field':
      requestBody = {
        idf_content: idfContent
        // weather_content intentionally omitted
      };
      break;
      
    case 'Invalid weather file format':
      requestBody = {
        idf_content: idfContent,
        weather_content: 'This is not a valid EPW file\nInvalid content'
      };
      break;
      
    default:
      throw new Error(`Unknown test case: ${testCase.name}`);
  }
  
  console.log(`\n📤 Sending request to API...`);
  console.log(`   IDF size: ${requestBody.idf_content.length} bytes`);
  console.log(`   Weather size: ${requestBody.weather_content?.length || 0} bytes`);
  
  if (requestBody.weather_content) {
    const validation = validateEPWFormat(requestBody.weather_content);
    if (validation.valid) {
      console.log(`   ✅ Weather file format appears valid`);
      const firstLine = requestBody.weather_content.split(/\r?\n/)[0];
      console.log(`   📍 First line: ${firstLine.substring(0, 80)}...`);
    } else {
      console.log(`   ⚠️  Weather file validation: ${validation.error}`);
    }
  } else {
    console.log(`   ⚠️  No weather content provided`);
  }
  
  try {
    const startTime = Date.now();
    const response = await fetch(ENERGYPLUS_API_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(requestBody)
    });
    
    const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
    console.log(`\n⏱️  Response received in ${elapsed}s`);
    console.log(`   Status: ${response.status} ${response.statusText}`);
    
    const responseText = await response.text();
    let result;
    
    try {
      result = JSON.parse(responseText);
    } catch (e) {
      console.log(`   ⚠️  Response is not JSON: ${responseText.substring(0, 200)}...`);
      result = { error: responseText };
    }
    
    if (response.ok) {
      console.log(`\n✅ Request succeeded`);
      console.log(`   Simulation status: ${result.simulation_status || 'unknown'}`);
      
      if (result.simulation_status === 'success') {
        console.log(`   ✅ Simulation completed successfully`);
        console.log(`   Total energy: ${result.total_energy_consumption || 'N/A'} kWh`);
        console.log(`   Building area: ${result.building_area || 'N/A'} m²`);
        
        // Check if weather was used
        if (result.stdout) {
          const stdoutLower = result.stdout.toLowerCase();
          if (stdoutLower.includes('weather') || stdoutLower.includes('.epw')) {
            console.log(`   ✅ Weather file appears to have been used (found in stdout)`);
          }
        }
        
        if (result.stderr) {
          const stderrLower = result.stderr.toLowerCase();
          if (stderrLower.includes('weather') || stderrLower.includes('epw')) {
            console.log(`   ⚠️  Weather-related messages in stderr`);
            console.log(`   ${result.stderr.substring(0, 200)}...`);
          }
        }
        
        return { success: true, result };
      } else {
        console.log(`   ❌ Simulation failed`);
        console.log(`   Error: ${result.error_message || result.error || 'Unknown error'}`);
        
        if (result.warnings && result.warnings.length > 0) {
          console.log(`   Warnings (${result.warnings.length}):`);
          result.warnings.slice(0, 3).forEach(w => {
            console.log(`     - ${w.substring(0, 80)}...`);
          });
        }
        
        if (result.errors && result.errors.length > 0) {
          console.log(`   Errors (${result.errors.length}):`);
          result.errors.slice(0, 3).forEach(e => {
            console.log(`     - ${e.substring(0, 80)}...`);
          });
        }
        
        return { success: false, result };
      }
    } else {
      console.log(`\n❌ Request failed`);
      console.log(`   Error: ${result.error || responseText.substring(0, 200)}`);
      return { success: false, error: result.error || responseText };
    }
    
  } catch (error) {
    console.log(`\n❌ Request error: ${error.message}`);
    return { success: false, error: error.message };
  }
}

async function main() {
  console.log('🧪 Weather File Handling Test Suite');
  console.log('='.repeat(70));
  console.log(`🌐 API URL: ${ENERGYPLUS_API_URL}`);
  
  // Load test files
  console.log('\n📁 Loading test files...');
  const idfPath = findTestIDF();
  const weatherPath = findTestWeather();
  
  console.log(`   ✅ IDF: ${idfPath}`);
  console.log(`   ✅ Weather: ${weatherPath}`);
  
  const idfContent = readFileSync(idfPath, 'utf-8');
  const weatherContent = readFileSync(weatherPath, 'utf-8');
  
  console.log(`   IDF size: ${idfContent.length} bytes`);
  console.log(`   Weather size: ${weatherContent.length} bytes`);
  
  // Validate weather file format
  const validation = validateEPWFormat(weatherContent);
  if (validation.valid) {
    console.log(`   ✅ Weather file format is valid`);
  } else {
    console.log(`   ⚠️  Weather file validation warning: ${validation.error}`);
  }
  
  // Run tests
  const results = [];
  
  for (const testCase of testCases) {
    const result = await runTest(testCase, idfContent, weatherContent);
    results.push({
      testCase: testCase.name,
      expectedPass: testCase.shouldPass,
      actualPass: result.success,
      match: testCase.shouldPass === result.success
    });
    
    // Brief pause between tests
    await new Promise(resolve => setTimeout(resolve, 2000));
  }
  
  // Summary
  console.log('\n\n');
  console.log('='.repeat(70));
  console.log('📊 TEST SUMMARY');
  console.log('='.repeat(70));
  
  results.forEach(r => {
    const status = r.match ? '✅' : '❌';
    console.log(`${status} ${r.testCase}`);
    console.log(`   Expected: ${r.expectedPass ? 'PASS' : 'FAIL'}, Actual: ${r.actualPass ? 'PASS' : 'FAIL'}`);
  });
  
  const allMatch = results.every(r => r.match);
  if (allMatch) {
    console.log('\n✅ All tests behaved as expected!');
  } else {
    console.log('\n⚠️  Some tests did not behave as expected');
  }
  
  console.log('\n' + '='.repeat(70));
}

main().catch(console.error);


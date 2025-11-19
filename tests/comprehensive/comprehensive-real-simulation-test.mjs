#!/usr/bin/env node
/**
 * Comprehensive Real Simulation Test Suite
 * Tests IDF Creator and EnergyPlus services with multiple addresses
 * Validates areas, energy results, and parameters for realism
 */

import { createClient } from '@supabase/supabase-js';
import { readFileSync, writeFileSync } from 'fs';
import dotenv from 'dotenv';

dotenv.config();

// Configuration
const ENERGYPLUS_API_URL = 'https://web-production-1d1be.up.railway.app/simulate';
const IDF_CREATOR_API_URL = 'https://web-production-3092c.up.railway.app';

const supabaseUrl = process.env.VITE_SUPABASE_URL;
const supabaseKey = process.env.VITE_SUPABASE_ANON_KEY;

// Supabase is optional - only needed for fallback generate-building function
let supabase = null;
if (supabaseUrl && supabaseKey) {
  supabase = createClient(supabaseUrl, supabaseKey);
  console.log('✅ Supabase credentials found - fallback available');
} else {
  console.log('⚠️  Supabase credentials not found - will use IDF Creator service only');
}

// Test cases based on available weather files
const TEST_CASES = [
  {
    name: 'Chicago Office Building',
    address: '100 N State St, Chicago, IL 60602',
    building_type: 'office',
    floor_area: 5000, // m²
    num_floors: 5,
    expected_weather: 'USA_IL_Chicago-OHare.Intl.AP.725300_TMY3.epw',
    expected_city: 'Chicago'
  },
  {
    name: 'San Francisco Office Building',
    address: '1 Market St, San Francisco, CA 94105',
    building_type: 'office',
    floor_area: 3000, // m²
    num_floors: 3,
    expected_weather: 'USA_CA_San.Francisco.Intl.AP.724940_TMY3.epw',
    expected_city: 'SanFrancisco'
  },
  {
    name: 'Chicago Retail Building',
    address: '200 N Michigan Ave, Chicago, IL 60601',
    building_type: 'retail',
    floor_area: 2000, // m²
    num_floors: 2,
    expected_weather: 'USA_IL_Chicago-OHare.Intl.AP.725300_TMY3.epw',
    expected_city: 'Chicago'
  }
];

// Test results storage
const testResults = {
  timestamp: new Date().toISOString(),
  testCases: [],
  summary: {
    total: 0,
    passed: 0,
    failed: 0,
    warnings: []
  },
  issues: []
};

/**
 * Validate IDF content for common issues
 */
function validateIDF(idfContent, testCase) {
  const issues = [];
  const warnings = [];
  
  // Check for hardcoded coordinates
  const latMatch = idfContent.match(/Site:Location[^;]*,\s*([\d.-]+),\s*([\d.-]+)/);
  if (latMatch) {
    const lat = parseFloat(latMatch[1]);
    const lon = parseFloat(latMatch[2]);
    
    // Chicago coordinates should be around 41.98, -87.92
    // San Francisco should be around 37.62, -122.38
    if (testCase.expected_city === 'Chicago' && (Math.abs(lat - 41.98) > 1 || Math.abs(lon + 87.92) > 1)) {
      warnings.push(`Location coordinates may be incorrect: ${lat}, ${lon} (expected ~41.98, -87.92 for Chicago)`);
    }
    if (testCase.expected_city === 'SanFrancisco' && (Math.abs(lat - 37.62) > 1 || Math.abs(lon + 122.38) > 1)) {
      warnings.push(`Location coordinates may be incorrect: ${lat}, ${lon} (expected ~37.62, -122.38 for San Francisco)`);
    }
  }
  
  // Check for unrealistic building areas
  const areaMatches = idfContent.match(/Zone[^;]*,\s*([^,]+)[^;]*;\s*[^;]*;\s*([\d.]+)/g);
  if (areaMatches) {
    areaMatches.forEach(match => {
      const areaMatch = match.match(/[\d.]+/g);
      if (areaMatch) {
        const area = parseFloat(areaMatch[areaMatch.length - 1]);
        if (area > 10000) {
          warnings.push(`Very large zone area detected: ${area} m² (may be unrealistic)`);
        }
        if (area < 10) {
          warnings.push(`Very small zone area detected: ${area} m² (may be unrealistic)`);
        }
      }
    });
  }
  
  // Check for missing HVAC systems
  if (!idfContent.includes('HVACTemplate') && !idfContent.includes('ZoneHVAC') && !idfContent.includes('HVACTemplate')) {
    warnings.push('No HVAC system detected in IDF - building will not have climate control');
  }
  
  // Check for missing schedules
  if (!idfContent.includes('Schedule:') && !idfContent.includes('ScheduleTypeLimits')) {
    warnings.push('No schedules detected - building will run 24/7 without realistic operations');
  }
  
  // Check for unrealistic material properties
  const uValueMatch = idfContent.match(/U-Factor[\s\S]*?,\s*([\d.]+)/);
  if (uValueMatch) {
    const uValue = parseFloat(uValueMatch[1]);
    if (uValue > 10) {
      issues.push(`Unrealistic U-value: ${uValue} W/m²K (typical windows: 1.5-3.0, walls: 0.2-0.5)`);
    }
  }
  
  // Check for missing output requests
  if (!idfContent.includes('Output:Variable') && !idfContent.includes('Output:Meter')) {
    warnings.push('No output variables or meters specified - limited simulation results will be available');
  }
  
  return { issues, warnings };
}

/**
 * Validate simulation results for realism
 */
function validateSimulationResults(results, testCase) {
  const issues = [];
  const warnings = [];
  
  if (!results || !results.summary) {
    issues.push('Simulation results missing summary data');
    return { issues, warnings };
  }
  
  const summary = results.summary;
  
  // Check total energy consumption
  if (summary.totalEnergyUse) {
    const energyMatch = summary.totalEnergyUse.match(/[\d,]+/);
    if (energyMatch) {
      const totalEnergy = parseFloat(energyMatch[0].replace(/,/g, '')); // kWh
      const buildingArea = testCase.floor_area * testCase.num_floors;
      const eui = (totalEnergy / buildingArea) * 1000; // kWh/m²/year
      
      // Typical office building EUI: 100-200 kWh/m²/year
      // Retail: 150-250 kWh/m²/year
      const expectedEUI = testCase.building_type === 'office' ? 150 : 200;
      
      if (eui < 50) {
        warnings.push(`Very low EUI: ${eui.toFixed(2)} kWh/m²/year (expected ~${expectedEUI} for ${testCase.building_type})`);
      } else if (eui > 500) {
        issues.push(`Very high EUI: ${eui.toFixed(2)} kWh/m²/year (expected ~${expectedEUI} for ${testCase.building_type}) - may indicate simulation error`);
      }
    }
  }
  
  // Check building area consistency
  if (summary.buildingArea) {
    const areaMatch = summary.buildingArea.match(/[\d,]+/);
    if (areaMatch) {
      const reportedArea = parseFloat(areaMatch[0].replace(/,/g, '')); // m²
      const expectedArea = testCase.floor_area * testCase.num_floors;
      const areaDiff = Math.abs(reportedArea - expectedArea) / expectedArea;
      
      if (areaDiff > 0.1) {
        warnings.push(`Building area mismatch: reported ${reportedArea} m², expected ${expectedArea} m² (${(areaDiff * 100).toFixed(1)}% difference)`);
      }
    }
  }
  
  // Check for zero or negative energy values
  ['heatingEnergy', 'coolingEnergy', 'lightingEnergy', 'equipmentEnergy'].forEach(key => {
    if (summary[key] && summary[key] !== 'N/A') {
      const energyMatch = summary[key].match(/[\d,]+/);
      if (energyMatch) {
        const energy = parseFloat(energyMatch[0].replace(/,/g, ''));
        if (energy < 0) {
          issues.push(`Negative energy value for ${key}: ${energy} kWh`);
        }
      }
    }
  });
  
  // Check peak demand
  if (summary.peakDemand && summary.peakDemand !== 'N/A') {
    const demandMatch = summary.peakDemand.match(/[\d.]+/);
    if (demandMatch) {
      const peakDemand = parseFloat(demandMatch[0]); // kW
      const buildingArea = testCase.floor_area * testCase.num_floors;
      const demandDensity = (peakDemand / buildingArea) * 1000; // W/m²
      
      // Typical office building peak demand: 20-50 W/m²
      if (demandDensity < 5) {
        warnings.push(`Very low peak demand density: ${demandDensity.toFixed(2)} W/m² (expected 20-50 W/m²)`);
      } else if (demandDensity > 200) {
        issues.push(`Very high peak demand density: ${demandDensity.toFixed(2)} W/m² (expected 20-50 W/m²) - may indicate error`);
      }
    }
  }
  
  return { issues, warnings };
}

/**
 * Test IDF Creator Service
 */
async function testIDFCreator(testCase) {
  console.log(`\n📝 Testing IDF Creator for: ${testCase.name}`);
  
  try {
    // Try to call IDF Creator service (if available)
    const response = await fetch(`${IDF_CREATOR_API_URL}/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        address: testCase.address,
        building_type: testCase.building_type,
        floor_area: testCase.floor_area,
        num_floors: testCase.num_floors
      })
    });
    
    if (!response.ok) {
      throw new Error(`IDF Creator API returned ${response.status}`);
    }
    
    const data = await response.json();
    
    if (!data.success) {
      throw new Error('IDF Creator did not return success');
    }
    
    // Service returns download_url, need to fetch the IDF file
    let idfContent;
    if (data.download_url) {
      const downloadUrl = `${IDF_CREATOR_API_URL}${data.download_url}`;
      console.log(`   Downloading IDF from: ${downloadUrl}`);
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
    
    // Validate IDF
    const validation = validateIDF(idfContent, testCase);
    
    return {
      success: true,
      idf_content: idfContent,
      parameters: data.parameters_used || data.parameters,
      validation
    };
    
  } catch (error) {
    console.log(`❌ IDF Creator service error: ${error.message}`);
    console.log(`   Service URL: ${IDF_CREATOR_API_URL}`);
    
    // Fallback: Use generate-building function if Supabase is available
    if (supabase) {
      console.log(`   Trying alternative: generate-building function`);
      try {
        const { data, error: funcError } = await supabase.functions.invoke('generate-building', {
          body: {
            userInput: `${testCase.address} - ${testCase.building_type} building, ${testCase.floor_area} m², ${testCase.num_floors} floors`,
            projectId: 'test-' + Date.now()
          }
        });
        
        if (funcError) throw funcError;
        
        // Download IDF from URL
        if (data.idfUrl) {
          const idfResponse = await fetch(data.idfUrl);
          const idfContent = await idfResponse.text();
          const validation = validateIDF(idfContent, testCase);
          
          return {
            success: true,
            idf_content: idfContent,
            parameters: data.extractedParams,
            validation,
            method: 'generate-building-function'
          };
        }
        
        throw new Error('No IDF URL returned');
        
      } catch (fallbackError) {
        return {
          success: false,
          error: `Both IDF Creator and generate-building failed: ${fallbackError.message}`
        };
      }
    } else {
      return {
        success: false,
        error: `IDF Creator service failed: ${error.message} (No Supabase fallback available)`
      };
    }
  }
}

/**
 * Get weather file for test case
 */
async function getWeatherFile(testCase) {
  console.log(`🌤️  Getting weather file for: ${testCase.expected_city}`);
  
  try {
    // Try to use local weather file first
    const localWeatherPath = `speed-build-engine/${testCase.expected_weather}`;
    try {
      const weatherContent = readFileSync(localWeatherPath, 'utf8');
      console.log(`✅ Using local weather file: ${localWeatherPath}`);
      return weatherContent;
    } catch (localError) {
      // Try alternative location
      const altPath = `EnergyPlus-MCP/energyplus-mcp-server/sample_files/${testCase.expected_weather}`;
      try {
        const weatherContent = readFileSync(altPath, 'utf8');
        console.log(`✅ Using local weather file: ${altPath}`);
        return weatherContent;
      } catch (altError) {
        // Download from NREL
        console.log(`📥 Downloading weather file from NREL...`);
        const weatherUrl = `https://raw.githubusercontent.com/NREL/EnergyPlus/develop/weather/${testCase.expected_weather}`;
        const response = await fetch(weatherUrl);
        
        if (!response.ok) {
          throw new Error(`Failed to download weather file: ${response.status}`);
        }
        
        const weatherContent = await response.text();
        console.log(`✅ Downloaded weather file: ${weatherContent.length} bytes`);
        return weatherContent;
      }
    }
  } catch (error) {
    throw new Error(`Failed to get weather file: ${error.message}`);
  }
}

/**
 * Test EnergyPlus Simulation
 */
async function testEnergyPlusSimulation(idfContent, weatherContent, testCase) {
  console.log(`⚡ Testing EnergyPlus simulation for: ${testCase.name}`);
  
  try {
    const requestBody = {
      idf_content: idfContent,
      weather_content: weatherContent
    };
    
    console.log(`📤 Sending simulation request to: ${ENERGYPLUS_API_URL}`);
    console.log(`   IDF size: ${idfContent.length} bytes`);
    console.log(`   Weather size: ${weatherContent.length} bytes`);
    
    const response = await fetch(ENERGYPLUS_API_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(requestBody)
    });
    
    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`EnergyPlus API error (${response.status}): ${errorText}`);
    }
    
    const results = await response.json();
    
    // Validate results
    const validation = validateSimulationResults(results, testCase);
    
    return {
      success: true,
      results,
      validation
    };
    
  } catch (error) {
    return {
      success: false,
      error: error.message
    };
  }
}

/**
 * Run complete test for a test case
 */
async function runTest(testCase) {
  console.log(`\n${'='.repeat(60)}`);
  console.log(`🧪 TEST: ${testCase.name}`);
  console.log(`${'='.repeat(60)}`);
  
  const testResult = {
    name: testCase.name,
    address: testCase.address,
    timestamp: new Date().toISOString(),
    idfCreator: null,
    energyPlus: null,
    issues: [],
    warnings: [],
    passed: false
  };
  
  try {
    // Step 1: Test IDF Creator
    const idfResult = await testIDFCreator(testCase);
    testResult.idfCreator = idfResult;
    
    if (!idfResult.success) {
      testResult.issues.push(`IDF Creator failed: ${idfResult.error}`);
      testResults.testCases.push(testResult);
      return testResult;
    }
    
    testResult.issues.push(...idfResult.validation.issues);
    testResult.warnings.push(...idfResult.validation.warnings);
    
    // Step 2: Get weather file
    const weatherContent = await getWeatherFile(testCase);
    
    // Step 3: Test EnergyPlus simulation
    const simResult = await testEnergyPlusSimulation(
      idfResult.idf_content,
      weatherContent,
      testCase
    );
    
    testResult.energyPlus = simResult;
    
    if (!simResult.success) {
      testResult.issues.push(`EnergyPlus simulation failed: ${simResult.error}`);
    } else {
      testResult.issues.push(...simResult.validation.issues);
      testResult.warnings.push(...simResult.validation.warnings);
    }
    
    // Determine if test passed
    testResult.passed = testResult.issues.length === 0;
    
    // Log results
    console.log(`\n📊 Results:`);
    console.log(`   IDF Creator: ${idfResult.success ? '✅' : '❌'}`);
    console.log(`   EnergyPlus: ${simResult.success ? '✅' : '❌'}`);
    console.log(`   Issues: ${testResult.issues.length}`);
    console.log(`   Warnings: ${testResult.warnings.length}`);
    
    if (simResult.success && simResult.results.summary) {
      console.log(`\n📈 Energy Results:`);
      console.log(`   Total Energy: ${simResult.results.summary.totalEnergyUse || 'N/A'}`);
      console.log(`   Building Area: ${simResult.results.summary.buildingArea || 'N/A'}`);
      console.log(`   Peak Demand: ${simResult.results.summary.peakDemand || 'N/A'}`);
    }
    
  } catch (error) {
    testResult.issues.push(`Test failed with exception: ${error.message}`);
    console.error(`❌ Test exception: ${error.message}`);
  }
  
  testResults.testCases.push(testResult);
  return testResult;
}

/**
 * Generate comprehensive report
 */
function generateReport() {
  console.log(`\n${'='.repeat(60)}`);
  console.log(`📋 COMPREHENSIVE TEST REPORT`);
  console.log(`${'='.repeat(60)}`);
  
  // Calculate summary
  testResults.summary.total = testResults.testCases.length;
  testResults.summary.passed = testResults.testCases.filter(t => t.passed).length;
  testResults.summary.failed = testResults.summary.total - testResults.summary.passed;
  
  // Collect all issues and warnings
  testResults.testCases.forEach(testCase => {
    testResults.summary.warnings.push(...testCase.warnings.map(w => ({ test: testCase.name, warning: w })));
    testResults.issues.push(...testCase.issues.map(i => ({ test: testCase.name, issue: i })));
  });
  
  // Generate report
  const report = {
    ...testResults,
    recommendations: []
  };
  
  // Analyze issues and generate recommendations
  const issueTypes = {};
  testResults.issues.forEach(({ issue }) => {
    const type = issue.split(':')[0];
    issueTypes[type] = (issueTypes[type] || 0) + 1;
  });
  
  // Add recommendations based on issues found
  if (testResults.issues.some(i => i.issue.includes('EUI'))) {
    report.recommendations.push({
      priority: 'HIGH',
      issue: 'Unrealistic Energy Use Intensity (EUI)',
      recommendation: 'Review building envelope properties, HVAC system efficiency, and schedules. Ensure materials and systems match real-world standards (ASHRAE 90.1).'
    });
  }
  
  if (testResults.issues.some(i => i.issue.includes('U-value') || i.issue.includes('material'))) {
    report.recommendations.push({
      priority: 'HIGH',
      issue: 'Unrealistic material properties',
      recommendation: 'Validate all material properties against ASHRAE standards. U-values for windows should be 1.5-3.0 W/m²K, walls 0.2-0.5 W/m²K.'
    });
  }
  
  if (testResults.issues.some(i => i.issue.includes('area'))) {
    report.recommendations.push({
      priority: 'MEDIUM',
      issue: 'Building area inconsistencies',
      recommendation: 'Ensure IDF zone areas match input parameters. Verify floor area calculations and zone definitions.'
    });
  }
  
  if (testResults.warnings.some(w => w.warning.includes('HVAC'))) {
    report.recommendations.push({
      priority: 'HIGH',
      issue: 'Missing or incomplete HVAC systems',
      recommendation: 'All buildings must have properly configured HVAC systems for realistic simulations. Add HVAC templates or zone equipment.'
    });
  }
  
  if (testResults.warnings.some(w => w.warning.includes('schedule'))) {
    report.recommendations.push({
      priority: 'HIGH',
      issue: 'Missing schedules',
      recommendation: 'Add realistic schedules for occupancy, lighting, and equipment. Buildings should not operate 24/7 without schedules.'
    });
  }
  
  // Save report
  const reportJson = JSON.stringify(report, null, 2);
  writeFileSync('comprehensive-test-report.json', reportJson);
  
  // Print summary
  console.log(`\n📊 SUMMARY:`);
  console.log(`   Total Tests: ${report.summary.total}`);
  console.log(`   Passed: ${report.summary.passed} ✅`);
  console.log(`   Failed: ${report.summary.failed} ❌`);
  console.log(`   Total Issues: ${report.issues.length}`);
  console.log(`   Total Warnings: ${report.summary.warnings.length}`);
  
  if (report.issues.length > 0) {
    console.log(`\n❌ CRITICAL ISSUES FOUND:`);
    report.issues.forEach(({ test, issue }, idx) => {
      console.log(`   ${idx + 1}. [${test}] ${issue}`);
    });
  }
  
  if (report.summary.warnings.length > 0) {
    console.log(`\n⚠️  WARNINGS:`);
    report.summary.warnings.slice(0, 10).forEach(({ test, warning }, idx) => {
      console.log(`   ${idx + 1}. [${test}] ${warning}`);
    });
    if (report.summary.warnings.length > 10) {
      console.log(`   ... and ${report.summary.warnings.length - 10} more warnings`);
    }
  }
  
  if (report.recommendations.length > 0) {
    console.log(`\n💡 RECOMMENDATIONS:`);
    report.recommendations.forEach((rec, idx) => {
      console.log(`\n   ${idx + 1}. [${rec.priority}] ${rec.issue}`);
      console.log(`      → ${rec.recommendation}`);
    });
  }
  
  console.log(`\n📄 Full report saved to: comprehensive-test-report.json`);
  
  return report;
}

/**
 * Main test execution
 */
async function main() {
  console.log('🚀 COMPREHENSIVE REAL SIMULATION TEST SUITE');
  console.log('=' .repeat(60));
  console.log(`\n📋 Configuration:`);
  console.log(`   EnergyPlus API: ${ENERGYPLUS_API_URL}`);
  console.log(`   IDF Creator API: ${IDF_CREATOR_API_URL}`);
  console.log(`   Test Cases: ${TEST_CASES.length}`);
  
  // Run all tests
  for (const testCase of TEST_CASES) {
    await runTest(testCase);
    // Small delay between tests
    await new Promise(resolve => setTimeout(resolve, 2000));
  }
  
  // Generate report
  const report = generateReport();
  
  // Exit with appropriate code
  process.exit(report.summary.failed > 0 ? 1 : 0);
}

// Run tests
main().catch(error => {
  console.error('❌ Test suite failed:', error);
  process.exit(1);
});


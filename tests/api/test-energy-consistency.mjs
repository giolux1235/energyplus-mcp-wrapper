#!/usr/bin/env node
/**
 * Test Energy Results Consistency
 * Compares results from multiple runs and checks for inconsistencies
 */

import { readFileSync } from 'fs';
import { join } from 'path';

const ENERGYPLUS_API_URL = 'https://web-production-1d1be.up.railway.app/simulate';
const WEATHER_FILE = 'EnergyPlus-MCP/energyplus-mcp-server/sample_files/USA_CA_San.Francisco.Intl.AP.724940_TMY3.epw';

/**
 * Get IDF from IDF Creator
 */
async function getIDFCreatorIDF() {
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
 * Run simulation
 */
async function runSimulation(idfContent, weatherContent) {
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
 * Analyze results
 */
function analyzeResults(results, testName) {
  console.log(`\n📊 ${testName} Analysis:`);
  console.log('=' .repeat(60));
  
  const totalEnergy = results.total_energy_consumption || 0;
  const heatingEnergy = results.heating_energy || 0;
  const coolingEnergy = results.cooling_energy || 0;
  const lightingEnergy = results.lighting_energy || 0;
  const equipmentEnergy = results.equipment_energy || 0;
  const buildingArea = results.building_area || 0;
  const eui = results.energy_intensity || results.energyUseIntensity || 0;
  
  console.log(`Energy Values:`);
  console.log(`  Total Energy: ${totalEnergy.toLocaleString()} kWh`);
  console.log(`  Heating: ${heatingEnergy.toLocaleString()} kWh`);
  console.log(`  Cooling: ${coolingEnergy.toLocaleString()} kWh`);
  console.log(`  Lighting: ${lightingEnergy.toLocaleString()} kWh`);
  console.log(`  Equipment: ${equipmentEnergy.toLocaleString()} kWh`);
  
  const sumOfComponents = heatingEnergy + coolingEnergy + lightingEnergy + equipmentEnergy;
  const difference = Math.abs(totalEnergy - sumOfComponents);
  const percentDiff = totalEnergy > 0 ? ((difference / totalEnergy) * 100).toFixed(2) : 0;
  
  console.log(`\nSum of Components: ${sumOfComponents.toLocaleString()} kWh`);
  console.log(`Difference: ${difference.toLocaleString()} kWh (${percentDiff}%)`);
  
  if (percentDiff > 10 && totalEnergy > 0) {
    console.log(`  ⚠️  WARNING: Large difference between total and sum of components!`);
  }
  
  console.log(`\nBuilding Metrics:`);
  console.log(`  Building Area: ${buildingArea.toLocaleString()} m²`);
  console.log(`  Energy Use Intensity: ${eui.toLocaleString()} kWh/m²`);
  
  if (buildingArea > 0) {
    const calculatedEUI = (totalEnergy / buildingArea).toFixed(2);
    console.log(`  Calculated EUI: ${calculatedEUI} kWh/m²`);
    
    if (eui > 0 && Math.abs(eui - parseFloat(calculatedEUI)) > 1) {
      console.log(`  ⚠️  WARNING: EUI mismatch! Calculated=${calculatedEUI}, Reported=${eui}`);
    }
  }
  
  // Check for 1-week simulation
  // Expected: ~1/52 of annual energy
  // Typical office: 100-300 kWh/m²/year
  // For 5000 m²: 500,000 - 1,500,000 kWh/year
  // For 1 week: ~9,600 - 28,800 kWh/week
  const expectedWeeklyRange = {
    min: (buildingArea * 100) / 52,  // Conservative estimate
    max: (buildingArea * 300) / 52   // High estimate
  };
  
  console.log(`\nValidation Checks:`);
  console.log(`  Expected Weekly Range: ${expectedWeeklyRange.min.toFixed(0)} - ${expectedWeeklyRange.max.toFixed(0)} kWh`);
  
  if (totalEnergy < expectedWeeklyRange.min * 0.5) {
    console.log(`  ⚠️  WARNING: Energy seems too low for 1-week simulation`);
  } else if (totalEnergy > expectedWeeklyRange.max * 1.5) {
    console.log(`  ⚠️  WARNING: Energy seems too high for 1-week simulation`);
  } else {
    console.log(`  ✅ Energy within expected range`);
  }
  
  // Check extraction method
  const extractionMethod = results._extraction_method || results.energy_results?.extraction_method || 'unknown';
  console.log(`\nExtraction Method: ${extractionMethod}`);
  
  // Check for missing values
  const missingValues = [];
  if (!results.heating_energy && results.heating_energy !== 0) missingValues.push('heating_energy');
  if (!results.cooling_energy && results.cooling_energy !== 0) missingValues.push('cooling_energy');
  if (!results.lighting_energy && results.lighting_energy !== 0) missingValues.push('lighting_energy');
  if (!results.equipment_energy && results.equipment_energy !== 0) missingValues.push('equipment_energy');
  
  if (missingValues.length > 0) {
    console.log(`  ⚠️  Missing energy breakdown values: ${missingValues.join(', ')}`);
  }
  
  return {
    totalEnergy,
    heatingEnergy,
    coolingEnergy,
    lightingEnergy,
    equipmentEnergy,
    buildingArea,
    eui,
    sumOfComponents,
    difference,
    percentDiff,
    extractionMethod,
    missingValues
  };
}

/**
 * Main
 */
async function main() {
  console.log('🚀 Energy Results Consistency Test');
  console.log('=' .repeat(60));
  
  // Test 1: IDF Creator file
  console.log('\n📋 Test 1: IDF Creator File');
  const idfCreatorIdf = await getIDFCreatorIDF();
  console.log(`   IDF Size: ${(idfCreatorIdf.length / 1024).toFixed(1)} KB`);
  
  const weatherContent = readFileSync(join(process.cwd(), WEATHER_FILE), 'utf-8');
  
  console.log('   ⚡ Running simulation...');
  const idfCreatorResults = await runSimulation(idfCreatorIdf, weatherContent);
  const idfCreatorAnalysis = analyzeResults(idfCreatorResults, 'IDF Creator Results');
  
  // Test 2: Simple IDF for comparison
  console.log('\n\n📋 Test 2: Simple IDF (5ZoneAirCooled)');
  const simpleIdf = readFileSync(join(process.cwd(), 'nrel_testfiles/5ZoneAirCooled.idf'), 'utf-8');
  console.log(`   IDF Size: ${(simpleIdf.length / 1024).toFixed(1)} KB`);
  
  console.log('   ⚡ Running simulation...');
  const simpleResults = await runSimulation(simpleIdf, weatherContent);
  const simpleAnalysis = analyzeResults(simpleResults, 'Simple IDF Results');
  
  // Comparison
  console.log('\n\n📊 Comparison');
  console.log('=' .repeat(60));
  console.log('Metric'.padEnd(25) + 'IDF Creator'.padEnd(20) + 'Simple IDF'.padEnd(20) + 'Ratio');
  console.log('-'.repeat(70));
  
  const metrics = [
    { name: 'Total Energy (kWh)', idf: idfCreatorAnalysis.totalEnergy, simple: simpleAnalysis.totalEnergy },
    { name: 'Building Area (m²)', idf: idfCreatorAnalysis.buildingArea, simple: simpleAnalysis.buildingArea },
    { name: 'EUI (kWh/m²)', idf: idfCreatorAnalysis.eui, simple: simpleAnalysis.eui },
    { name: 'Heating (kWh)', idf: idfCreatorAnalysis.heatingEnergy, simple: simpleAnalysis.heatingEnergy },
    { name: 'Cooling (kWh)', idf: idfCreatorAnalysis.coolingEnergy, simple: simpleAnalysis.coolingEnergy },
    { name: 'Lighting (kWh)', idf: idfCreatorAnalysis.lightingEnergy, simple: simpleAnalysis.lightingEnergy },
  ];
  
  for (const metric of metrics) {
    const ratio = metric.simple > 0 ? (metric.idf / metric.simple).toFixed(2) : 'N/A';
    console.log(
      metric.name.padEnd(25) + 
      metric.idf.toLocaleString().padEnd(20) + 
      metric.simple.toLocaleString().padEnd(20) + 
      ratio
    );
  }
  
  // Final summary
  console.log('\n\n✅ Test Complete!');
  console.log('=' .repeat(60));
  
  // Check for inconsistencies
  const issues = [];
  
  if (idfCreatorAnalysis.percentDiff > 10) {
    issues.push('IDF Creator: Large difference between total and sum of components');
  }
  
  if (simpleAnalysis.percentDiff > 10) {
    issues.push('Simple IDF: Large difference between total and sum of components');
  }
  
  if (idfCreatorAnalysis.missingValues.length > 0) {
    issues.push(`IDF Creator: Missing energy breakdown values (${idfCreatorAnalysis.missingValues.join(', ')})`);
  }
  
  if (simpleAnalysis.missingValues.length > 0) {
    issues.push(`Simple IDF: Missing energy breakdown values (${simpleAnalysis.missingValues.join(', ')})`);
  }
  
  if (issues.length > 0) {
    console.log('\n⚠️  Potential Issues Found:');
    issues.forEach(issue => console.log(`  - ${issue}`));
  } else {
    console.log('\n✅ No major inconsistencies detected!');
  }
}

main().catch(error => {
  console.error('\n❌ Test Failed:', error);
  process.exit(1);
});



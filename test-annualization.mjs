#!/usr/bin/env node
/**
 * Test annualization fix - verify EUI values are reasonable after fix
 */

import { readFileSync, existsSync } from 'fs';
import { join, basename } from 'path';

const API_URL = 'https://web-production-1d1be.up.railway.app/simulate';

async function testAnnualization() {
  console.log('🧪 Testing Energy Annualization Fix');
  console.log('='.repeat(70));
  
  // Test with LgOffVAV (the one that showed 0.91 EUI before)
  const idfPath = join(process.cwd(), 'EnergyPlus-MCP/energyplus-mcp-server/sample_files/LgOffVAV.idf');
  const weatherPath = join(process.cwd(), 'EnergyPlus-MCP/energyplus-mcp-server/sample_files/USA_CA_San.Francisco.Intl.AP.724940_TMY3.epw');
  
  if (!existsSync(idfPath) || !existsSync(weatherPath)) {
    console.error('❌ Test files not found');
    process.exit(1);
  }
  
  const idfContent = readFileSync(idfPath, 'utf-8');
  const weatherContent = readFileSync(weatherPath, 'utf-8');
  
  console.log(`📄 IDF: ${basename(idfPath)}`);
  console.log(`🌤️  Weather: ${basename(weatherPath)}`);
  console.log(`\n📤 Sending to API...`);
  
  const startTime = Date.now();
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
  console.log(`📊 Status: ${response.status}`);
  
  if (!response.ok) {
    const errorText = await response.text();
    console.error(`❌ API Error: ${errorText}`);
    process.exit(1);
  }
  
  const result = await response.json();
  
  console.log(`\n📊 Results:`);
  console.log(`   Simulation status: ${result.simulation_status}`);
  
  if (result.simulation_status !== 'success') {
    console.error(`❌ Simulation failed: ${result.error_message || result.error}`);
    process.exit(1);
  }
  
  const totalEnergy = result.total_energy_consumption || result.energy_results?.total_site_energy_kwh || 0;
  const buildingArea = result.building_area || result.energy_results?.building_area_m2 || 0;
  const eui = result.energy_intensity || result.energy_results?.eui_kwh_m2 || 0;
  
  console.log(`\n📈 Energy Values:`);
  console.log(`   Total Energy: ${totalEnergy.toLocaleString()} kWh`);
  console.log(`   Building Area: ${buildingArea.toLocaleString()} m²`);
  console.log(`   EUI: ${eui.toFixed(2)} kWh/m²/year`);
  
  // Validation
  console.log(`\n✅ Validation:`);
  
  // Check if EUI is reasonable (20-300 kWh/m²/year for office buildings)
  if (eui < 20) {
    console.log(`   ❌ EUI too low: ${eui.toFixed(2)} kWh/m²/year (expected 20-300)`);
    console.log(`   ⚠️  This suggests energy was NOT annualized properly`);
    process.exit(1);
  } else if (eui > 300) {
    console.log(`   ⚠️  EUI very high: ${eui.toFixed(2)} kWh/m²/year (expected 20-300)`);
    console.log(`   This might be correct for high-energy buildings`);
  } else {
    console.log(`   ✅ EUI is reasonable: ${eui.toFixed(2)} kWh/m²/year`);
  }
  
  // Check if total energy makes sense for annual
  // For 8,361 m² building, annual energy should be roughly:
  // Low: 8,361 × 50 = 418,050 kWh/year
  // High: 8,361 × 200 = 1,672,200 kWh/year
  const expectedMin = buildingArea * 50;
  const expectedMax = buildingArea * 200;
  
  if (totalEnergy < expectedMin * 0.5) {
    console.log(`   ⚠️  Total energy seems low for annual: ${totalEnergy.toLocaleString()} kWh`);
    console.log(`   Expected range: ${expectedMin.toLocaleString()} - ${expectedMax.toLocaleString()} kWh/year`);
    console.log(`   This might indicate weekly values not annualized`);
  } else if (totalEnergy > expectedMax * 2) {
    console.log(`   ⚠️  Total energy seems high: ${totalEnergy.toLocaleString()} kWh`);
    console.log(`   Expected range: ${expectedMin.toLocaleString()} - ${expectedMax.toLocaleString()} kWh/year`);
  } else {
    console.log(`   ✅ Total energy is reasonable for annual: ${totalEnergy.toLocaleString()} kWh`);
  }
  
  // Calculate EUI manually to verify
  const calculatedEUI = totalEnergy / buildingArea;
  console.log(`\n🔍 Verification:`);
  console.log(`   Calculated EUI: ${calculatedEUI.toFixed(2)} kWh/m²/year`);
  console.log(`   Reported EUI: ${eui.toFixed(2)} kWh/m²/year`);
  
  if (Math.abs(calculatedEUI - eui) > 0.1) {
    console.log(`   ⚠️  EUI mismatch! Calculated vs Reported differ by ${Math.abs(calculatedEUI - eui).toFixed(2)}`);
  } else {
    console.log(`   ✅ EUI calculation matches`);
  }
  
  // Check energy_results object
  if (result.energy_results) {
    console.log(`\n📋 Energy Results Object:`);
    console.log(`   Total Site Energy: ${result.energy_results.total_site_energy_kwh?.toLocaleString()} kWh`);
    console.log(`   EUI: ${result.energy_results.eui_kwh_m2?.toFixed(2)} kWh/m²/year`);
    
    if (result.energy_results.eui_kwh_m2 < 20) {
      console.log(`   ❌ Energy results EUI too low!`);
      process.exit(1);
    }
  }
  
  console.log(`\n✅ All checks passed! Annualization is working correctly.`);
  console.log('='.repeat(70));
}

testAnnualization().catch(error => {
  console.error('❌ Test failed:', error);
  process.exit(1);
});


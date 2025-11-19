#!/usr/bin/env node
/**
 * Analyze API response to understand energy values
 */

import { readFileSync, existsSync } from 'fs';
import { join, basename } from 'path';

const API_URL = 'https://web-production-1d1be.up.railway.app/simulate';

async function analyzeResponse() {
  const idfPath = join(process.cwd(), 'EnergyPlus-MCP/energyplus-mcp-server/sample_files/LgOffVAV.idf');
  const weatherPath = join(process.cwd(), 'EnergyPlus-MCP/energyplus-mcp-server/sample_files/USA_CA_San.Francisco.Intl.AP.724940_TMY3.epw');
  
  const idfContent = readFileSync(idfPath, 'utf-8');
  const weatherContent = readFileSync(weatherPath, 'utf-8');
  
  console.log('📤 Sending request...');
  const response = await fetch(API_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      idf_content: idfContent,
      weather_content: weatherContent
    })
  });
  
  const result = await response.json();
  
  console.log('\n📊 Full Response Analysis:');
  console.log('='.repeat(70));
  
  console.log('\n1. Top-level fields:');
  console.log(`   total_energy_consumption: ${result.total_energy_consumption?.toLocaleString()} kWh`);
  console.log(`   building_area: ${result.building_area?.toLocaleString()} m²`);
  console.log(`   energy_intensity: ${result.energy_intensity} kWh/m²/year`);
  
  console.log('\n2. Energy Results Object:');
  if (result.energy_results) {
    console.log(`   total_site_energy_kwh: ${result.energy_results.total_site_energy_kwh?.toLocaleString()} kWh`);
    console.log(`   building_area_m2: ${result.energy_results.building_area_m2?.toLocaleString()} m²`);
    console.log(`   eui_kwh_m2: ${result.energy_results.eui_kwh_m2} kWh/m²/year`);
  }
  
  console.log('\n3. Breakdown:');
  console.log(`   heating_energy: ${result.heating_energy?.toLocaleString()} kWh`);
  console.log(`   cooling_energy: ${result.cooling_energy?.toLocaleString()} kWh`);
  console.log(`   lighting_energy: ${result.lighting_energy?.toLocaleString()} kWh`);
  console.log(`   equipment_energy: ${result.equipment_energy?.toLocaleString()} kWh`);
  
  if (result.energy_results) {
    console.log('\n4. Energy Results Breakdown:');
    console.log(`   heating_energy: ${result.energy_results.heating_energy?.toLocaleString()} kWh`);
    console.log(`   cooling_energy: ${result.energy_results.cooling_energy?.toLocaleString()} kWh`);
    console.log(`   lighting_energy: ${result.energy_results.lighting_energy?.toLocaleString()} kWh`);
    console.log(`   equipment_energy: ${result.energy_results.equipment_energy?.toLocaleString()} kWh`);
  }
  
  console.log('\n5. Calculations:');
  const buildingArea = result.building_area || result.energy_results?.building_area_m2 || 8361.27;
  
  if (result.total_energy_consumption) {
    const eui1 = result.total_energy_consumption / buildingArea;
    console.log(`   EUI from total_energy_consumption: ${eui1.toFixed(2)} kWh/m²/year`);
  }
  
  if (result.energy_results?.total_site_energy_kwh) {
    const eui2 = result.energy_results.total_site_energy_kwh / buildingArea;
    console.log(`   EUI from energy_results.total_site_energy_kwh: ${eui2.toFixed(2)} kWh/m²/year`);
  }
  
  console.log('\n6. Expected values (if weekly energy was 7,575 kWh):');
  const weeklyEnergy = 7575.01;
  const annualEnergy = weeklyEnergy * 52;
  const expectedEUI = annualEnergy / buildingArea;
  console.log(`   Weekly energy: ${weeklyEnergy.toLocaleString()} kWh`);
  console.log(`   Annualized: ${annualEnergy.toLocaleString()} kWh`);
  console.log(`   Expected EUI: ${expectedEUI.toFixed(2)} kWh/m²/year`);
  
  console.log('\n' + '='.repeat(70));
}

analyzeResponse().catch(console.error);


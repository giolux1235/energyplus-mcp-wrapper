#!/usr/bin/env node
/**
 * Extract energy and analyze warnings from a successful simulation
 */

const ENERGYPLUS_API_URL = 'https://web-production-1d1be.up.railway.app/simulate';

import { readFileSync } from 'fs';
import { join } from 'path';

async function analyzeResults() {
  
  // Get IDF
  console.log('Getting IDF...');
  const r = await fetch('https://web-production-3092c.up.railway.app/generate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ address: '123 Test', building_type: 'office', floor_area: 5000, num_floors: 5 })
  });
  const d = await r.json();
  const idf = await (await fetch(`https://web-production-3092c.up.railway.app${d.download_url}`)).text();
  
  // Run simulation
  const weather = readFileSync(join(process.cwd(), 'EnergyPlus-MCP/energyplus-mcp-server/sample_files/USA_CA_San.Francisco.Intl.AP.724940_TMY3.epw'), 'utf-8');
  console.log('Running simulation...');
  const res = await fetch(ENERGYPLUS_API_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ idf_content: idf, weather_content: weather })
  });
  const results = await res.json();
  
  if (results.simulation_status !== 'success') {
    console.error('Simulation failed:', results.error_message);
    process.exit(1);
  }
  
  console.log('\n=== ENERGY RESULTS ===');
  console.log('Total Energy:', results.total_energy_consumption?.toLocaleString(), 'kWh');
  console.log('Building Area:', results.building_area?.toLocaleString(), 'm²');
  console.log('EUI:', results.energy_intensity?.toLocaleString(), 'kWh/m²');
  console.log('Breakdown:');
  console.log('  Heating:', results.heating_energy || 0, 'kWh');
  console.log('  Cooling:', results.cooling_energy || 0, 'kWh');
  console.log('  Lighting:', results.lighting_energy || 0, 'kWh');
  console.log('  Equipment:', results.equipment_energy || 0, 'kWh');
  
  // Energy validation
  const totalEnergy = results.total_energy_consumption || 0;
  const buildingArea = results.building_area || 0;
  if (buildingArea > 0) {
    const expectedWeeklyMin = (7 / 365.0) * 100 * buildingArea;
    const expectedWeeklyMax = (7 / 365.0) * 300 * buildingArea;
    console.log('\nExpected Range (1 week):', expectedWeeklyMin.toFixed(0), '-', expectedWeeklyMax.toFixed(0), 'kWh');
    
    if (totalEnergy > expectedWeeklyMax * 10) {
      console.log('🔴 ISSUE: Energy is', (totalEnergy / expectedWeeklyMax).toFixed(1), 'x higher than expected!');
      console.log('   This suggests annual totals instead of weekly totals');
    } else if (totalEnergy > expectedWeeklyMax * 2) {
      console.log('⚠️  WARNING: Energy is', (totalEnergy / expectedWeeklyMax).toFixed(1), 'x higher than expected');
    } else {
      console.log('✅ Energy within reasonable range');
    }
  }
  
  // Warnings analysis
  console.log('\n=== WARNINGS ANALYSIS ===');
  console.log('API Reported Warnings:', results.warnings_count || 0);
  
  if (results.error_file_content) {
    const err = results.error_file_content;
    console.log('Error file length:', err.length, 'chars');
    
    // Parse warnings
    const lines = err.split('\n');
    const warnings = lines.filter(l => l.includes('** Warning'));
    const severe = lines.filter(l => l.includes('** Severe'));
    const fatal = lines.filter(l => l.includes('** Fatal'));
    
    console.log('Error File Warnings:', warnings.length);
    console.log('Severe Warnings:', severe.length);
    console.log('Fatal Errors:', fatal.length);
    
    if (fatal.length > 0) {
      console.log('\n🔴 FATAL ERRORS:');
      fatal.slice(0, 10).forEach((f, i) => console.log(`  ${i+1}. ${f.substring(0, 120)}`));
    }
    
    if (severe.length > 0) {
      console.log('\n🔴 SEVERE WARNINGS:');
      severe.slice(0, 20).forEach((s, i) => console.log(`  ${i+1}. ${s.substring(0, 120)}`));
    }
    
    if (warnings.length > 0) {
      console.log('\n⚠️  WARNINGS (showing first 30):');
      warnings.slice(0, 30).forEach((w, i) => console.log(`  ${i+1}. ${w.substring(0, 120)}`));
      
      // Categorize
      const categories = {
        missing: warnings.filter(w => w.toLowerCase().includes('missing') || w.toLowerCase().includes('not found')),
        invalid: warnings.filter(w => w.toLowerCase().includes('invalid') || w.toLowerCase().includes('illegal')),
        schedule: warnings.filter(w => w.toLowerCase().includes('schedule')),
        material: warnings.filter(w => w.toLowerCase().includes('material') || w.toLowerCase().includes('construction')),
        hvac: warnings.filter(w => w.toLowerCase().includes('hvac') || w.toLowerCase().includes('system')),
        geometry: warnings.filter(w => w.toLowerCase().includes('surface') || w.toLowerCase().includes('zone')),
        output: warnings.filter(w => w.toLowerCase().includes('output') || w.toLowerCase().includes('variable')),
      };
      
      console.log('\n📊 Warning Categories:');
      Object.entries(categories).forEach(([cat, items]) => {
        if (items.length > 0) {
          console.log(`  ${cat}: ${items.length}`);
        }
      });
      
      // Summary
      console.log('\n=== SUMMARY ===');
      const issues = [];
      if (fatal.length > 0) issues.push(`🔴 FATAL: ${fatal.length} fatal errors`);
      if (severe.length > 0) issues.push(`🔴 SEVERE: ${severe.length} severe warnings`);
      if (warnings.length > 100) issues.push(`⚠️  Many warnings: ${warnings.length}`);
      if (categories.missing.length > 10) issues.push(`⚠️  Missing objects: ${categories.missing.length}`);
      if (categories.invalid.length > 10) issues.push(`⚠️  Invalid values: ${categories.invalid.length}`);
      const expectedWeeklyMax = buildingArea > 0 ? (7 / 365.0) * 300 * buildingArea : 0;
      if (expectedWeeklyMax > 0 && totalEnergy > expectedWeeklyMax * 10) issues.push(`🔴 Energy extraction issue: Annual totals detected`);
      
      if (issues.length > 0) {
        console.log('Issues Found:');
        issues.forEach(i => console.log(`  ${i}`));
        console.log('\n💡 Recommendation: Review with IDF Creator team');
      } else {
        console.log('✅ No serious issues detected');
      }
    } else {
      console.log('✅ No warnings found in error file');
    }
  } else {
    console.log('⚠️  No error_file_content in response');
  }
}

analyzeResults().catch(console.error);


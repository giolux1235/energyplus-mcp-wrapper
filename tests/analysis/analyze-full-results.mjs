#!/usr/bin/env node
/**
 * Full Analysis: Energy Results + Warnings
 * Extracts complete error file and analyzes all warnings
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
 * Parse error file content
 */
function parseErrorFile(errorContent) {
  if (!errorContent) return { warnings: [], severe: [], fatal: [] };
  
  const lines = errorContent.split('\n');
  const warnings = [];
  const severe = [];
  const fatal = [];
  
  for (const line of lines) {
    if (line.includes('**  Fatal') || line.includes('** Fatal')) {
      fatal.push(line.trim());
    } else if (line.includes('** Severe')) {
      severe.push(line.trim());
    } else if (line.includes('** Warning')) {
      warnings.push(line.trim());
    }
  }
  
  return { warnings, severe, fatal };
}

/**
 * Analyze energy results
 */
function analyzeEnergy(results) {
  console.log('\n📊 Energy Results Analysis');
  console.log('=' .repeat(60));
  
  const totalEnergy = results.total_energy_consumption || 0;
  const buildingArea = results.building_area || 0;
  const eui = results.energy_intensity || results.energyUseIntensity || 0;
  
  console.log(`Total Energy: ${totalEnergy.toLocaleString()} kWh`);
  console.log(`Building Area: ${buildingArea.toLocaleString()} m²`);
  console.log(`EUI: ${eui.toLocaleString()} kWh/m²`);
  
  // Validation
  if (buildingArea > 0) {
    const expectedWeeklyMin = (7 / 365.0) * 100 * buildingArea;
    const expectedWeeklyMax = (7 / 365.0) * 300 * buildingArea;
    
    console.log(`\nExpected Range (1 week): ${expectedWeeklyMin.toFixed(0)} - ${expectedWeeklyMax.toFixed(0)} kWh`);
    
    if (totalEnergy > expectedWeeklyMax * 10) {
      console.log(`🔴 ISSUE: Energy is ${(totalEnergy / expectedWeeklyMax).toFixed(1)}x higher than expected!`);
      console.log(`   This suggests annual totals instead of weekly totals`);
      console.log(`   Correction needed: ${totalEnergy} * (7/365) = ${(totalEnergy * 7 / 365).toFixed(2)} kWh`);
    } else if (totalEnergy > expectedWeeklyMax * 2) {
      console.log(`⚠️  WARNING: Energy is ${(totalEnergy / expectedWeeklyMax).toFixed(1)}x higher than expected`);
    } else {
      console.log(`✅ Energy within reasonable range`);
    }
  }
  
  // Breakdown
  console.log(`\nEnergy Breakdown:`);
  console.log(`  Heating: ${(results.heating_energy || 0).toLocaleString()} kWh`);
  console.log(`  Cooling: ${(results.cooling_energy || 0).toLocaleString()} kWh`);
  console.log(`  Lighting: ${(results.lighting_energy || 0).toLocaleString()} kWh`);
  console.log(`  Equipment: ${(results.equipment_energy || 0).toLocaleString()} kWh`);
  
  const sumOfComponents = (results.heating_energy || 0) + 
                         (results.cooling_energy || 0) + 
                         (results.lighting_energy || 0) + 
                         (results.equipment_energy || 0);
  
  if (sumOfComponents === 0 && totalEnergy > 0) {
    console.log(`\n⚠️  WARNING: Total energy exists but breakdown is all zeros`);
    console.log(`   This suggests extraction issue with breakdown values`);
  }
}

/**
 * Main
 */
async function main() {
  console.log('🚀 Full EnergyPlus Results Analysis');
  console.log('=' .repeat(60));
  
  try {
    // Get IDF
    console.log('\n📥 Getting IDF from Creator service...');
    const idfContent = await getIDFCreatorIDF();
    console.log(`   ✅ IDF: ${(idfContent.length / 1024).toFixed(1)} KB`);
    
    // Run simulation
    console.log('\n⚡ Running simulation...');
    const weatherContent = readFileSync(join(process.cwd(), WEATHER_FILE), 'utf-8');
    
    let results;
    try {
      results = await runSimulation(idfContent, weatherContent);
    } catch (error) {
      console.error(`❌ Simulation request failed: ${error.message}`);
      throw error;
    }
    
    if (results.simulation_status !== 'success') {
      // Even if failed, try to extract error file if available
      if (results.error_file_content) {
        console.log('⚠️  Simulation reported failure, but extracting error file...');
        const { warnings, severe, fatal } = parseErrorFile(results.error_file_content);
        console.log(`   Found ${warnings.length} warnings, ${severe.length} severe, ${fatal.length} fatal`);
      }
      throw new Error(`Simulation failed: ${results.error_message || 'Unknown'}`);
    }
    
    console.log('✅ Simulation completed\n');
    
    // Analyze energy
    analyzeEnergy(results);
    
    // Analyze warnings
    console.log('\n\n📋 Warning Analysis');
    console.log('=' .repeat(60));
    
    const errorContent = results.error_file_content || '';
    const { warnings, severe, fatal } = parseErrorFile(errorContent);
    
    const apiWarnings = results.warnings || [];
    const apiWarningsCount = results.warnings_count || 0;
    
    console.log(`API Reported Warnings: ${apiWarningsCount}`);
    console.log(`Error File Warnings: ${warnings.length}`);
    console.log(`Severe Warnings: ${severe.length}`);
    console.log(`Fatal Errors: ${fatal.length}`);
    
    if (fatal.length > 0) {
      console.log(`\n🔴 FATAL ERRORS (${fatal.length}):`);
      fatal.slice(0, 10).forEach(e => console.log(`   - ${e}`));
    }
    
    if (severe.length > 0) {
      console.log(`\n🔴 SEVERE WARNINGS (${severe.length}):`);
      severe.slice(0, 20).forEach(w => console.log(`   - ${w}`));
      if (severe.length > 20) {
        console.log(`   ... and ${severe.length - 20} more`);
      }
    }
    
    // Categorize warnings
    const categories = {
      missing: [],
      invalid: [],
      schedule: [],
      material: [],
      hvac: [],
      geometry: [],
      output: [],
      other: []
    };
    
    if (warnings.length > 0) {
      console.log(`\n⚠️  WARNINGS (${warnings.length}):`);
      
      for (const warning of warnings) {
        const w = warning.toLowerCase();
        if (w.includes('missing') || w.includes('not found')) {
          categories.missing.push(warning);
        } else if (w.includes('invalid') || w.includes('illegal')) {
          categories.invalid.push(warning);
        } else if (w.includes('schedule')) {
          categories.schedule.push(warning);
        } else if (w.includes('material') || w.includes('construction')) {
          categories.material.push(warning);
        } else if (w.includes('hvac') || w.includes('system')) {
          categories.hvac.push(warning);
        } else if (w.includes('surface') || w.includes('zone')) {
          categories.geometry.push(warning);
        } else if (w.includes('output') || w.includes('variable')) {
          categories.output.push(warning);
        } else {
          categories.other.push(warning);
        }
      }
      
      if (categories.missing.length > 0) {
        console.log(`\n   Missing Objects (${categories.missing.length}):`);
        categories.missing.slice(0, 10).forEach(w => console.log(`      - ${w}`));
      }
      
      if (categories.invalid.length > 0) {
        console.log(`\n   Invalid Values (${categories.invalid.length}):`);
        categories.invalid.slice(0, 10).forEach(w => console.log(`      - ${w}`));
      }
      
      if (categories.hvac.length > 0) {
        console.log(`\n   HVAC Issues (${categories.hvac.length}):`);
        categories.hvac.slice(0, 10).forEach(w => console.log(`      - ${w}`));
      }
      
      if (categories.other.length > 0 && categories.other.length < 50) {
        console.log(`\n   Other (${categories.other.length}):`);
        categories.other.slice(0, 10).forEach(w => console.log(`      - ${w}`));
      }
    }
    
    // Summary
    console.log('\n\n📊 Summary & Recommendations');
    console.log('=' .repeat(60));
    
    const issues = [];
    
    if (fatal.length > 0) {
      issues.push(`🔴 FATAL: ${fatal.length} fatal errors - simulation may be invalid`);
    }
    
    if (severe.length > 0) {
      issues.push(`🔴 SEVERE: ${severe.length} severe warnings - needs review`);
    }
    
    if (warnings.length > 100) {
      issues.push(`⚠️  Many warnings (${warnings.length}) - IDF quality concerns`);
    }
    
    if (categories.missing.length > 10) {
      issues.push(`⚠️  Missing objects (${categories.missing.length}) - IDF may be incomplete`);
    }
    
    if (categories.invalid.length > 10) {
      issues.push(`⚠️  Invalid values (${categories.invalid.length}) - data quality issues`);
    }
    
    const totalEnergy = results.total_energy_consumption || 0;
    const buildingArea = results.building_area || 0;
    if (buildingArea > 0) {
      const expectedMax = (7 / 365.0) * 300 * buildingArea;
      if (totalEnergy > expectedMax * 10) {
        issues.push(`🔴 Energy extraction issue: Value appears to be annual total, not weekly`);
      }
    }
    
    if (issues.length > 0) {
      console.log('Issues Found:');
      issues.forEach(issue => console.log(`   ${issue}`));
      console.log('\n💡 Recommendation: Review with IDF Creator team');
      console.log('   - Check for missing required objects');
      console.log('   - Validate material/construction definitions');
      console.log('   - Review HVAC system configurations');
      console.log('   - Verify schedule completeness');
    } else {
      console.log('✅ No serious issues detected');
      console.log('   Warnings appear to be minor/non-critical');
    }
    
    console.log('\n✅ Analysis Complete!');
    
  } catch (error) {
    console.error('\n❌ Analysis Failed:', error.message);
    process.exit(1);
  }
}

main();


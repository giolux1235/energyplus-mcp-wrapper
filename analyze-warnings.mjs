#!/usr/bin/env node
/**
 * Analyze EnergyPlus Warnings
 * Runs simulation and extracts warnings for analysis
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
 * Analyze warnings
 */
function analyzeWarnings(warnings, errorFileContent) {
  console.log('\n📊 Warning Analysis');
  console.log('=' .repeat(60));
  
  if (!warnings || warnings.length === 0) {
    console.log('✅ No warnings found');
    return;
  }
  
  console.log(`Total Warnings: ${warnings.length}\n`);
  
  // Categorize warnings
  const categories = {
    severe: [],
    missing: [],
    invalid: [],
    schedule: [],
    material: [],
    hvac: [],
    geometry: [],
    output: [],
    other: []
  };
  
  for (const warning of warnings) {
    const warningLower = warning.toLowerCase();
    
    if (warningLower.includes('severe')) {
      categories.severe.push(warning);
    } else if (warningLower.includes('missing') || warningLower.includes('not found')) {
      categories.missing.push(warning);
    } else if (warningLower.includes('invalid') || warningLower.includes('illegal')) {
      categories.invalid.push(warning);
    } else if (warningLower.includes('schedule')) {
      categories.schedule.push(warning);
    } else if (warningLower.includes('material') || warningLower.includes('construction')) {
      categories.material.push(warning);
    } else if (warningLower.includes('hvac') || warningLower.includes('system') || warningLower.includes('zone equipment')) {
      categories.hvac.push(warning);
    } else if (warningLower.includes('surface') || warningLower.includes('zone') || warningLower.includes('geometry')) {
      categories.geometry.push(warning);
    } else if (warningLower.includes('output') || warningLower.includes('variable') || warningLower.includes('meter')) {
      categories.output.push(warning);
    } else {
      categories.other.push(warning);
    }
  }
  
  // Report by category
  let seriousIssues = [];
  
  if (categories.severe.length > 0) {
    console.log(`🔴 SEVERE WARNINGS (${categories.severe.length}):`);
    categories.severe.forEach(w => console.log(`   - ${w}`));
    seriousIssues.push(`Severe warnings: ${categories.severe.length}`);
    console.log('');
  }
  
  if (categories.missing.length > 0) {
    console.log(`⚠️  MISSING OBJECTS (${categories.missing.length}):`);
    categories.missing.slice(0, 10).forEach(w => console.log(`   - ${w}`));
    if (categories.missing.length > 10) {
      console.log(`   ... and ${categories.missing.length - 10} more`);
    }
    if (categories.missing.length > 5) {
      seriousIssues.push(`Many missing objects: ${categories.missing.length}`);
    }
    console.log('');
  }
  
  if (categories.invalid.length > 0) {
    console.log(`❌ INVALID VALUES (${categories.invalid.length}):`);
    categories.invalid.slice(0, 10).forEach(w => console.log(`   - ${w}`));
    if (categories.invalid.length > 10) {
      console.log(`   ... and ${categories.invalid.length - 10} more`);
    }
    seriousIssues.push(`Invalid values: ${categories.invalid.length}`);
    console.log('');
  }
  
  if (categories.schedule.length > 0) {
    console.log(`📅 SCHEDULE ISSUES (${categories.schedule.length}):`);
    categories.schedule.slice(0, 5).forEach(w => console.log(`   - ${w}`));
    console.log('');
  }
  
  if (categories.material.length > 0) {
    console.log(`🧱 MATERIAL/CONSTRUCTION ISSUES (${categories.material.length}):`);
    categories.material.slice(0, 5).forEach(w => console.log(`   - ${w}`));
    console.log('');
  }
  
  if (categories.hvac.length > 0) {
    console.log(`❄️  HVAC ISSUES (${categories.hvac.length}):`);
    categories.hvac.slice(0, 5).forEach(w => console.log(`   - ${w}`));
    if (categories.hvac.length > 10) {
      seriousIssues.push(`Many HVAC issues: ${categories.hvac.length}`);
    }
    console.log('');
  }
  
  if (categories.geometry.length > 0) {
    console.log(`📐 GEOMETRY ISSUES (${categories.geometry.length}):`);
    categories.geometry.slice(0, 5).forEach(w => console.log(`   - ${w}`));
    console.log('');
  }
  
  if (categories.output.length > 0) {
    console.log(`📊 OUTPUT ISSUES (${categories.output.length}):`);
    categories.output.slice(0, 5).forEach(w => console.log(`   - ${w}`));
    console.log('');
  }
  
  if (categories.other.length > 0) {
    console.log(`ℹ️  OTHER WARNINGS (${categories.other.length}):`);
    categories.other.slice(0, 10).forEach(w => console.log(`   - ${w}`));
    console.log('');
  }
  
  // Summary
  console.log('📋 Summary');
  console.log('=' .repeat(60));
  console.log(`Total Warnings: ${warnings.length}`);
  console.log(`Severe: ${categories.severe.length}`);
  console.log(`Missing Objects: ${categories.missing.length}`);
  console.log(`Invalid Values: ${categories.invalid.length}`);
  console.log(`HVAC Issues: ${categories.hvac.length}`);
  console.log(`Other: ${categories.other.length}`);
  
  if (seriousIssues.length > 0) {
    console.log('\n🔴 SERIOUS ISSUES DETECTED:');
    seriousIssues.forEach(issue => console.log(`   - ${issue}`));
    console.log('\n💡 Recommendation: Review these issues with IDF Creator team');
  } else if (warnings.length > 50) {
    console.log('\n⚠️  Many warnings (>50) - may indicate IDF quality issues');
    console.log('   Consider reviewing with IDF Creator team');
  } else {
    console.log('\n✅ Warnings appear to be minor/non-critical');
  }
  
  return {
    total: warnings.length,
    categories,
    seriousIssues: seriousIssues.length > 0,
    recommendation: seriousIssues.length > 0 ? 'Review with IDF Creator team' : 
                   (warnings.length > 50 ? 'Consider review' : 'Minor issues')
  };
}

/**
 * Main
 */
async function main() {
  console.log('🚀 EnergyPlus Warning Analysis');
  console.log('=' .repeat(60));
  
  try {
    // Get IDF
    console.log('\n📥 Getting IDF from Creator service...');
    const idfContent = await getIDFCreatorIDF();
    console.log(`   ✅ IDF: ${(idfContent.length / 1024).toFixed(1)} KB`);
    
    // Run simulation
    console.log('\n⚡ Running simulation...');
    const weatherContent = readFileSync(join(process.cwd(), WEATHER_FILE), 'utf-8');
    const results = await runSimulation(idfContent, weatherContent);
    
    if (results.simulation_status !== 'success') {
      throw new Error(`Simulation failed: ${results.error_message || 'Unknown'}`);
    }
    
    console.log('✅ Simulation completed');
    console.log(`   Total Energy: ${results.total_energy_consumption?.toLocaleString() || 'N/A'} kWh`);
    console.log(`   Building Area: ${results.building_area?.toLocaleString() || 'N/A'} m²`);
    console.log(`   Warnings: ${results.warnings_count || 0}`);
    
    // Analyze warnings
    const warnings = results.warnings || [];
    const errorFileContent = results.error_file_content || '';
    
    const analysis = analyzeWarnings(warnings, errorFileContent);
    
    // Check error file for additional context
    if (errorFileContent) {
      const errorLines = errorFileContent.split('\n');
      const fatalErrors = errorLines.filter(l => l.includes('** Fatal'));
      const severeWarnings = errorLines.filter(l => l.includes('** Severe'));
      
      if (fatalErrors.length > 0) {
        console.log('\n🔴 FATAL ERRORS IN ERROR FILE:');
        fatalErrors.slice(0, 5).forEach(e => console.log(`   - ${e}`));
      }
      
      if (severeWarnings.length > warnings.length) {
        console.log(`\n⚠️  More severe warnings in error file (${severeWarnings.length}) than returned (${warnings.length})`);
      }
    }
    
    console.log('\n✅ Analysis Complete!');
    console.log('=' .repeat(60));
    
  } catch (error) {
    console.error('\n❌ Analysis Failed:', error.message);
    process.exit(1);
  }
}

main();


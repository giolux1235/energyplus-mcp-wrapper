#!/usr/bin/env node
/**
 * Run multiple tests to check consistency and validate results
 */

import { exec } from 'child_process';
import { promisify } from 'util';

const execAsync = promisify(exec);

async function runTest(address, testNumber) {
  console.log(`\n${'='.repeat(70)}`);
  console.log(`TEST ${testNumber}: ${address}`);
  console.log('='.repeat(70));
  
  try {
    const { stdout, stderr } = await execAsync(
      `node test-local-simulation-from-idf-creator.mjs`,
      { maxBuffer: 10 * 1024 * 1024 }
    );
    
    // Extract key results
    const results = {
      address,
      success: stdout.includes('✅ Simulation Status: SUCCESS'),
      totalEnergy: extractValue(stdout, 'Total Energy:', 'kWh'),
      electricity: extractValue(stdout, 'Electricity:', 'kWh'),
      gas: extractValue(stdout, 'Natural Gas:', 'kWh'),
      elapsedTime: extractValue(stdout, 'Elapsed Time:', 's'),
      output: stdout
    };
    
    return results;
  } catch (error) {
    return {
      address,
      success: false,
      error: error.message,
      output: error.stdout || ''
    };
  }
}

function extractValue(text, label, unit) {
  const regex = new RegExp(`${label}\\s+([\\d,]+(?:\\.[\\d]+)?)\\s*${unit}`);
  const match = text.match(regex);
  return match ? parseFloat(match[1].replace(/,/g, '')) : null;
}

async function main() {
  const addresses = [
    '233 S Wacker Dr, Chicago, IL 60606',
    '350 N Orleans St, Chicago, IL 60654',
    '1 N Dearborn St, Chicago, IL 60602'
  ];
  
  console.log('🧪 Running Multiple Tests for Consistency Check');
  console.log('='.repeat(70));
  
  const results = [];
  
  for (let i = 0; i < addresses.length; i++) {
    const result = await runTest(addresses[i], i + 1);
    results.push(result);
    
    // Brief pause between tests
    if (i < addresses.length - 1) {
      console.log('\n⏸️  Waiting 5 seconds before next test...');
      await new Promise(resolve => setTimeout(resolve, 5000));
    }
  }
  
  // Summary
  console.log('\n\n');
  console.log('📊 TEST SUMMARY');
  console.log('='.repeat(70));
  
  const successful = results.filter(r => r.success);
  const failed = results.filter(r => !r.success);
  
  console.log(`\n✅ Successful tests: ${successful.length}/${results.length}`);
  console.log(`❌ Failed tests: ${failed.length}/${results.length}`);
  
  if (successful.length > 0) {
    console.log('\n📈 Energy Consumption Comparison:');
    console.log('-'.repeat(70));
    console.log('Address'.padEnd(40) + 'Total (kWh)'.padEnd(15) + 'Time (s)');
    console.log('-'.repeat(70));
    
    successful.forEach((r, i) => {
      const addr = r.address.substring(0, 38);
      const total = r.totalEnergy ? r.totalEnergy.toLocaleString() : 'N/A';
      const time = r.elapsedTime ? r.elapsedTime.toFixed(1) : 'N/A';
      console.log(`${addr.padEnd(40)}${total.padEnd(15)}${time}`);
    });
    
    // Check consistency
    if (successful.length >= 2) {
      const totalEnergies = successful.map(r => r.totalEnergy).filter(v => v !== null);
      if (totalEnergies.length >= 2) {
        const min = Math.min(...totalEnergies);
        const max = Math.max(...totalEnergies);
        const avg = totalEnergies.reduce((a, b) => a + b, 0) / totalEnergies.length;
        const variance = totalEnergies.reduce((sum, val) => sum + Math.pow(val - avg, 2), 0) / totalEnergies.length;
        const stdDev = Math.sqrt(variance);
        const cv = (stdDev / avg) * 100; // Coefficient of variation
        
        console.log('\n📊 Statistical Analysis:');
        console.log(`   Average Total Energy: ${avg.toLocaleString(undefined, {maximumFractionDigits: 2})} kWh`);
        console.log(`   Range: ${min.toLocaleString()} - ${max.toLocaleString()} kWh`);
        console.log(`   Standard Deviation: ${stdDev.toLocaleString(undefined, {maximumFractionDigits: 2})} kWh`);
        console.log(`   Coefficient of Variation: ${cv.toFixed(2)}%`);
        
        if (cv > 50) {
          console.log('\n⚠️  WARNING: High variability detected (>50% CV). Results may not be consistent.');
        } else if (cv > 20) {
          console.log('\n⚠️  WARNING: Moderate variability detected (>20% CV).');
        } else {
          console.log('\n✅ Results are relatively consistent.');
        }
      }
    }
  }
  
  if (failed.length > 0) {
    console.log('\n❌ Failed Tests:');
    failed.forEach(r => {
      console.log(`   ${r.address}: ${r.error || 'Unknown error'}`);
    });
  }
  
  // Check for anomalies
  console.log('\n🔍 Anomaly Detection:');
  console.log('-'.repeat(70));
  
  const issues = [];
  
  successful.forEach(r => {
    // Check if energy values are suspiciously low
    if (r.totalEnergy && r.totalEnergy < 1000) {
      issues.push(`${r.address}: Total energy very low (${r.totalEnergy.toLocaleString()} kWh) for 5000 m² office`);
    }
    
    // Check if simulation time is suspiciously short
    if (r.elapsedTime && r.elapsedTime < 10) {
      issues.push(`${r.address}: Simulation completed very quickly (${r.elapsedTime}s) - may indicate issues`);
    }
    
    // Check if energy values are suspiciously high
    if (r.totalEnergy && r.totalEnergy > 10000000) {
      issues.push(`${r.address}: Total energy very high (${r.totalEnergy.toLocaleString()} kWh) - may indicate errors`);
    }
  });
  
  if (issues.length > 0) {
    console.log('⚠️  Potential Issues Found:');
    issues.forEach(issue => console.log(`   - ${issue}`));
  } else {
    console.log('✅ No obvious anomalies detected.');
  }
  
  console.log('\n' + '='.repeat(70));
}

main().catch(console.error);





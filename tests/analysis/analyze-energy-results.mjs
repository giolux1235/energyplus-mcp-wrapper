#!/usr/bin/env node
/**
 * Analyze energy simulation results for coherence
 */

const testResults = [
  {
    name: '1ZoneUncontrolled',
    totalEnergy: 38104.25,
    buildingArea: 232.26,
    eui: 164.06
  },
  {
    name: '5ZoneAirCooled',
    totalEnergy: 50583.29,
    buildingArea: 927.2,
    eui: 54.55
  },
  {
    name: 'LgOffVAV',
    totalEnergy: 7575.01,
    buildingArea: 8361.27,
    eui: 0.91
  }
];

console.log('📊 Energy Results Analysis');
console.log('='.repeat(70));

// Typical EUI ranges for different building types
const typicalEUI = {
  'office': { min: 50, max: 200, typical: 100 },
  'retail': { min: 60, max: 150, typical: 90 },
  'warehouse': { min: 20, max: 80, typical: 40 },
  'residential': { min: 30, max: 100, typical: 60 }
};

testResults.forEach(result => {
  console.log(`\n${result.name}:`);
  console.log(`  Total Energy: ${result.totalEnergy.toLocaleString()} kWh`);
  console.log(`  Building Area: ${result.buildingArea.toLocaleString()} m²`);
  console.log(`  EUI: ${result.eui.toFixed(2)} kWh/m²/year`);
  
  // Check if EUI makes sense
  const isReasonable = result.eui >= 20 && result.eui <= 300;
  const isVeryLow = result.eui < 20;
  const isVeryHigh = result.eui > 300;
  
  if (isVeryLow) {
    console.log(`  ⚠️  EUI is VERY LOW (${result.eui.toFixed(2)} kWh/m²/year)`);
    console.log(`     Expected range: 50-200 kWh/m²/year for typical office`);
    
    // Check if this might be weekly energy instead of annual
    const weeklyEnergy = result.totalEnergy;
    const annualizedEnergy = weeklyEnergy * 52;
    const annualizedEUI = annualizedEnergy / result.buildingArea;
    
    console.log(`  🔍 Possible Issue: Energy might be weekly instead of annual`);
    console.log(`     If weekly: ${weeklyEnergy.toLocaleString()} kWh/week`);
    console.log(`     Annualized: ${annualizedEnergy.toLocaleString()} kWh/year`);
    console.log(`     Annualized EUI: ${annualizedEUI.toFixed(2)} kWh/m²/year`);
    
    if (annualizedEUI >= 20 && annualizedEUI <= 300) {
      console.log(`     ✅ Annualized EUI looks reasonable!`);
    }
  } else if (isVeryHigh) {
    console.log(`  ⚠️  EUI is VERY HIGH (${result.eui.toFixed(2)} kWh/m²/year)`);
    console.log(`     Expected range: 50-200 kWh/m²/year for typical office`);
  } else if (isReasonable) {
    console.log(`  ✅ EUI is within reasonable range`);
  }
  
  // Calculate expected weekly energy if simulation ran for 1 week
  const expectedWeeklyMin = (result.buildingArea * 50) / 52; // Conservative
  const expectedWeeklyMax = (result.buildingArea * 200) / 52; // High estimate
  
  console.log(`  📅 Expected Weekly Range (if 1-week sim): ${expectedWeeklyMin.toFixed(0)} - ${expectedWeeklyMax.toFixed(0)} kWh`);
  
  if (result.totalEnergy < expectedWeeklyMin * 0.5) {
    console.log(`  ⚠️  Energy seems too low for 1-week simulation`);
  } else if (result.totalEnergy > expectedWeeklyMax * 2) {
    console.log(`  ⚠️  Energy seems too high for 1-week simulation`);
    console.log(`     Might be annual totals instead of weekly`);
  } else {
    console.log(`  ✅ Energy within expected weekly range`);
  }
});

console.log('\n' + '='.repeat(70));
console.log('\n🔍 Summary:');
console.log('='.repeat(70));

const lowEUI = testResults.filter(r => r.eui < 20);
const reasonableEUI = testResults.filter(r => r.eui >= 20 && r.eui <= 300);
const highEUI = testResults.filter(r => r.eui > 300);

if (lowEUI.length > 0) {
  console.log(`\n⚠️  ${lowEUI.length} result(s) with suspiciously low EUI:`);
  lowEUI.forEach(r => {
    console.log(`   - ${r.name}: ${r.eui.toFixed(2)} kWh/m²/year`);
    console.log(`     Likely issue: Weekly energy not annualized`);
    const annualized = (r.totalEnergy * 52) / r.buildingArea;
    console.log(`     If annualized: ${annualized.toFixed(2)} kWh/m²/year`);
  });
}

if (reasonableEUI.length > 0) {
  console.log(`\n✅ ${reasonableEUI.length} result(s) with reasonable EUI:`);
  reasonableEUI.forEach(r => {
    console.log(`   - ${r.name}: ${r.eui.toFixed(2)} kWh/m²/year`);
  });
}

if (highEUI.length > 0) {
  console.log(`\n⚠️  ${highEUI.length} result(s) with suspiciously high EUI:`);
  highEUI.forEach(r => {
    console.log(`   - ${r.name}: ${r.eui.toFixed(2)} kWh/m²/year`);
  });
}

console.log('\n' + '='.repeat(70));


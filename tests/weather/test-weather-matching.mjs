#!/usr/bin/env node
/**
 * Test weather file matching logic
 */

import { existsSync, readdirSync } from 'fs';
import { join, basename } from 'path';

// Test weather file matching logic
function findLocalWeatherFiles() {
  const weatherFiles = [];
  const dirs = [
    'EnergyPlus-MCP/energyplus-mcp-server/sample_files',
    'ashrae901_weather'
  ];
  
  for (const dir of dirs) {
    const fullPath = join(process.cwd(), dir);
    if (!existsSync(fullPath)) continue;
    try {
      const files = readdirSync(fullPath);
      for (const file of files) {
        if (file.toLowerCase().endsWith('.epw')) {
          weatherFiles.push(join(fullPath, file));
        }
      }
    } catch (e) {}
  }
  return weatherFiles.sort();
}

function matchWeatherFile(idfPath) {
  const idfName = basename(idfPath).toLowerCase();
  const weatherFiles = findLocalWeatherFiles();
  
  // Try to match by location name in filename (check most specific first)
  if (idfName.includes('san.francisco') || idfName.includes('sanfrancisco') || idfName.includes('sf')) {
    const sfWeather = weatherFiles.find(w => w.toLowerCase().includes('san.francisco') || w.toLowerCase().includes('sanfrancisco'));
    if (sfWeather) return sfWeather;
  }
  if (idfName.includes('denver') || idfName.includes('golden')) {
    const denverWeather = weatherFiles.find(w => w.toLowerCase().includes('denver') || w.toLowerCase().includes('golden'));
    if (denverWeather) return denverWeather;
  }
  if (idfName.includes('chicago')) {
    const chicagoWeather = weatherFiles.find(w => w.toLowerCase().includes('chicago'));
    if (chicagoWeather) return chicagoWeather;
  }
  
  // Default to first available weather file
  return weatherFiles[0] || null;
}

console.log('🧪 Testing Weather File Matching Logic\n');
console.log('='.repeat(70));

const weatherFiles = findLocalWeatherFiles();
console.log('\nAvailable weather files:');
weatherFiles.forEach(w => console.log('  -', basename(w)));

const testCases = [
  { idf: 'test_san_francisco.idf', expected: 'san.francisco' },
  { idf: 'test_denver.idf', expected: 'denver' },
  { idf: 'test_chicago.idf', expected: 'chicago' },
  { idf: 'test_golden.idf', expected: 'denver' },
  { idf: 'test_sf.idf', expected: 'san.francisco' },
  { idf: 'random_file.idf', expected: 'default' }
];

console.log('\n' + '='.repeat(70));
testCases.forEach(({ idf, expected }) => {
  const matched = matchWeatherFile(idf);
  const matchedName = matched ? basename(matched).toLowerCase() : 'none';
  const correct = 
    (expected === 'san.francisco' && matchedName.includes('san.francisco')) ||
    (expected === 'denver' && (matchedName.includes('denver') || matchedName.includes('golden'))) ||
    (expected === 'chicago' && matchedName.includes('chicago')) ||
    (expected === 'default' && matched !== null);
  
  const status = correct ? '✅' : '❌';
  console.log(`${status} IDF: ${idf}`);
  console.log(`   Expected: ${expected}, Got: ${matched ? basename(matched) : 'None'}`);
});

console.log('\n' + '='.repeat(70));


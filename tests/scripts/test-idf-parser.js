// Test IDF Parser
import { readFileSync } from 'fs';
import { IDFParser } from './supabase/functions/generate-compliance-pdf/idf-parser.ts';

console.log('🧪 Testing IDF Parser with NREL Building');
console.log('=' .repeat(60));

try {
  // Read the NREL IDF file
  console.log('📖 Reading IDF file...');
  const idfContent = readFileSync('RefBldgLargeOfficeNew2004_Chicago.idf', 'utf8');
  
  // Parse it
  console.log('🔍 Parsing IDF content...');
  const parser = new IDFParser(idfContent);
  const specs = parser.parse();
  
  console.log('');
  console.log('✅ PARSING COMPLETE!');
  console.log('=' .repeat(60));
  console.log('');
  
  console.log('🏗️  BUILDING SPECIFICATIONS:');
  console.log('  Floor Area:', specs.building.floorArea.toLocaleString(), 'sq ft');
  console.log('  Number of Stories:', specs.building.numberOfStories);
  console.log('  Building Type:', specs.building.buildingType);
  console.log('');
  
  console.log('🧱 ENVELOPE:');
  console.log('  Walls - R-value:', specs.envelope.walls.rvalue);
  console.log('  Roof - R-value:', specs.envelope.roof.rvalue);
  console.log('  Windows - U-factor:', specs.envelope.windows.uFactor);
  console.log('');
  
  console.log('🌡️  HVAC:');
  console.log('  Cooling Type:', specs.hvac.cooling.type);
  console.log('  Cooling COP:', specs.hvac.cooling.cop);
  console.log('  System Type:', specs.hvac.systemType);
  console.log('');
  
  console.log('💡 LIGHTING:');
  console.log('  Power Density:', specs.lighting.powerDensity, 'W/sq ft');
  console.log('  Fixture Type:', specs.lighting.fixtureType);
  console.log('');
  
  console.log('🔌 EQUIPMENT:');
  console.log('  Power Density:', specs.equipment.powerDensity, 'W/sq ft');
  console.log('');
  
  console.log('✅ All building data extracted successfully!');
  
} catch (error) {
  console.error('❌ Error:', error.message);
  console.error(error.stack);
}

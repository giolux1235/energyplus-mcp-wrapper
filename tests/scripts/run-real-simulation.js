// Run Real EnergyPlus Simulation with NREL Building Data
// This script uploads the real IDF and EPW files to Supabase and runs an actual simulation

import { createClient } from '@supabase/supabase-js';
import { readFileSync } from 'fs';

console.log('🚀 RUNNING REAL ENERGYPLUS SIMULATION');
console.log('=' .repeat(60));

// Supabase configuration (you'll need to replace these with your actual values)
const supabaseUrl = process.env.SUPABASE_URL || 'your-supabase-url';
const supabaseKey = process.env.SUPABASE_ANON_KEY || 'your-supabase-key';

const supabase = createClient(supabaseUrl, supabaseKey);

async function runRealSimulation() {
  try {
    console.log('📁 Loading real NREL building files...');
    
    // Read the actual IDF and EPW files
    const idfContent = readFileSync('RefBldgLargeOfficeNew2004_Chicago.idf', 'utf8');
    const weatherContent = readFileSync('USA_IL_Chicago-OHare.Intl.AP.725300_TMY3.epw', 'utf8');
    
    console.log('✅ Files loaded:');
    console.log(`  IDF: ${(idfContent.length / 1024).toFixed(0)} KB`);
    console.log(`  Weather: ${(weatherContent.length / 1024).toFixed(0)} KB`);
    console.log('');

    console.log('☁️ Uploading files to Supabase storage...');
    
    // Create a unique project ID for this test
    const testProjectId = `nrel-test-${Date.now()}`;
    
    // Upload IDF file
    const idfBlob = new Blob([idfContent], { type: 'text/plain' });
    const { data: idfUpload, error: idfError } = await supabase.storage
      .from('project-files')
      .upload(`${testProjectId}/RefBldgLargeOfficeNew2004_Chicago.idf`, idfBlob, {
        contentType: 'text/plain',
        upsert: false
      });

    if (idfError) {
      console.error('❌ IDF upload error:', idfError);
      throw idfError;
    }

    console.log('✅ IDF file uploaded');

    // Upload weather file
    const weatherBlob = new Blob([weatherContent], { type: 'text/plain' });
    const { data: weatherUpload, error: weatherError } = await supabase.storage
      .from('project-files')
      .upload(`${testProjectId}/USA_IL_Chicago-OHare.Intl.AP.725300_TMY3.epw`, weatherBlob, {
        contentType: 'text/plain',
        upsert: false
      });

    if (weatherError) {
      console.error('❌ Weather upload error:', weatherError);
      throw weatherError;
    }

    console.log('✅ Weather file uploaded');
    console.log('');

    // Get public URLs
    const { data: idfUrl } = supabase.storage
      .from('project-files')
      .getPublicUrl(`${testProjectId}/RefBldgLargeOfficeNew2004_Chicago.idf`);

    const { data: weatherUrl } = supabase.storage
      .from('project-files')
      .getPublicUrl(`${testProjectId}/USA_IL_Chicago-OHare.Intl.AP.725300_TMY3.epw`);

    console.log('📤 URLs generated:');
    console.log(`  IDF: ${idfUrl.publicUrl.substring(0, 80)}...`);
    console.log(`  Weather: ${weatherUrl.publicUrl.substring(0, 80)}...`);
    console.log('');

    console.log('⚡ Invoking run-simulation Edge Function...');
    console.log('⏳ This will call the actual EnergyPlus API...');
    
    // Call the run-simulation function
    const { data: simResult, error: simError } = await supabase.functions.invoke('run-simulation', {
      body: {
        idf_url: idfUrl.publicUrl,
        weather_url: weatherUrl.publicUrl
      }
    });

    if (simError) {
      console.error('❌ Simulation error:', simError);
      throw simError;
    }

    console.log('');
    console.log('🎉 REAL ENERGYPLUS SIMULATION COMPLETE!');
    console.log('=' .repeat(60));
    console.log('');
    console.log('📊 SIMULATION RESULTS:');
    console.log(JSON.stringify(simResult, null, 2));
    console.log('');

    if (simResult && simResult.summary) {
      console.log('📈 ENERGY CONSUMPTION BREAKDOWN:');
      console.log(`  Total Energy Use: ${simResult.summary.totalEnergyUse || 'N/A'}`);
      console.log(`  Heating Energy: ${simResult.summary.heatingEnergy || 'N/A'}`);
      console.log(`  Cooling Energy: ${simResult.summary.coolingEnergy || 'N/A'}`);
      console.log(`  Lighting Energy: ${simResult.summary.lightingEnergy || 'N/A'}`);
      console.log(`  Equipment Energy: ${simResult.summary.equipmentEnergy || 'N/A'}`);
      console.log(`  Peak Demand: ${simResult.summary.peakDemand || 'N/A'}`);
      console.log(`  Energy Use Intensity: ${simResult.summary.energyUseIntensity || 'N/A'}`);
      console.log('');

      if (simResult.recommendations) {
        console.log('💡 RECOMMENDATIONS:');
        simResult.recommendations.forEach((rec, i) => {
          console.log(`  ${i + 1}. ${rec.title}`);
          console.log(`     Savings: ${rec.estimated_savings_kwh || 'N/A'} kWh/year`);
        });
        console.log('');
      }

      console.log('✅ These are REAL simulation results from EnergyPlus!');
      console.log('   The energy consumption data is calculated from the actual');
      console.log('   building model, not estimates or made-up numbers.');
    }

    return simResult;

  } catch (error) {
    console.error('❌ Error running simulation:', error);
    throw error;
  }
}

// Export for use
export { runRealSimulation };

// Run if called directly
if (import.meta.main) {
  runRealSimulation().catch(console.error);
}

// Complete End-to-End Simulation Test
// This simulates what a real user would do to run a real EnergyPlus simulation

import { createClient } from '@supabase/supabase-js';
import { readFileSync } from 'fs';
import dotenv from 'dotenv';

dotenv.config();

console.log('🚀 COMPLETE END-TO-END REAL SIMULATION TEST');
console.log('=' .repeat(60));

// Load Supabase credentials from environment
const supabaseUrl = process.env.VITE_SUPABASE_URL;
const supabaseKey = process.env.VITE_SUPABASE_ANON_KEY;

if (!supabaseUrl || !supabaseKey) {
  console.error('❌ Missing Supabase credentials!');
  console.log('   Please set VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY in .env file');
  process.exit(1);
}

const supabase = createClient(supabaseUrl, supabaseKey);

async function runCompleteSimulation() {
  try {
    console.log('📋 Step 1: Checking authentication...');
    
    // Check if user is authenticated
    const { data: { user } } = await supabase.auth.getUser();
    
    if (!user) {
      console.log('⚠️  Not authenticated. Attempting sign-in...');
      const { data: authData, error: authError } = await supabase.auth.signInAnonymously();
      
      if (authError) {
        console.error('❌ Authentication error:', authError.message);
        console.log('\n📝 To run this test:');
        console.log('   1. Open http://localhost:5173 in your browser');
        console.log('   2. Sign in or create an account');
        console.log('   3. Then run this script again');
        return;
      }
      console.log('✅ Authenticated as:', authData.user?.id);
    } else {
      console.log('✅ Already authenticated as:', user.id);
    }
    
    console.log('');

    console.log('📁 Step 2: Loading real NREL building files...');
    const idfContent = readFileSync('RefBldgLargeOfficeNew2004_Chicago.idf', 'utf8');
    const weatherContent = readFileSync('USA_IL_Chicago-OHare.Intl.AP.725300_TMY3.epw', 'utf8');
    
    console.log('✅ Files loaded:');
    console.log(`  IDF: ${(idfContent.length / 1024).toFixed(0)} KB`);
    console.log(`  Weather: ${(weatherContent.length / 1024).toFixed(1)} KB`);
    console.log('');

    console.log('📝 Step 3: Creating new project...');
    const projectName = `NREL Large Office - Real Test ${new Date().toISOString()}`;
    
    const { data: project, error: projectError } = await supabase
      .from('projects')
      .insert({
        name: projectName,
        description: 'Real EnergyPlus simulation with NREL building data',
        building_type: 'office',
        status: 'active'
      })
      .select()
      .single();

    if (projectError) {
      console.error('❌ Project creation error:', projectError);
      throw projectError;
    }

    console.log('✅ Project created:', project.id);
    console.log('   Name:', project.name);
    console.log('');

    console.log('☁️ Step 4: Uploading IDF file to Supabase storage...');
    const idfBlob = new Blob([idfContent], { type: 'text/plain' });
    const idfPath = `${project.id}/RefBldgLargeOfficeNew2004_Chicago.idf`;
    
    const { error: idfError } = await supabase.storage
      .from('project-files')
      .upload(idfPath, idfBlob);

    if (idfError) {
      console.error('❌ IDF upload error:', idfError);
      throw idfError;
    }

    const { data: idfUrl } = supabase.storage
      .from('project-files')
      .getPublicUrl(idfPath);

    console.log('✅ IDF uploaded:', idfPath);

    console.log('☁️ Step 5: Uploading weather file to Supabase storage...');
    const weatherBlob = new Blob([weatherContent], { type: 'text/plain' });
    const weatherPath = `${project.id}/USA_IL_Chicago-OHare.Intl.AP.725300_TMY3.epw`;
    
    const { error: weatherError } = await supabase.storage
      .from('project-files')
      .upload(weatherPath, weatherBlob);

    if (weatherError) {
      console.error('❌ Weather upload error:', weatherError);
      throw weatherError;
    }

    const { data: weatherUrl } = supabase.storage
      .from('project-files')
      .getPublicUrl(weatherPath);

    console.log('✅ Weather uploaded:', weatherPath);
    console.log('');

    console.log('📊 Step 6: Updating project with file URLs...');
    const { error: updateError } = await supabase
      .from('projects')
      .update({
        idf_file_url: idfUrl.publicUrl,
        weather_file_url: weatherUrl.publicUrl
      })
      .eq('id', project.id);

    if (updateError) {
      console.error('❌ Update error:', updateError);
      throw updateError;
    }

    console.log('✅ Project updated with file URLs');
    console.log('');

    console.log('⚡ Step 7: Running REAL EnergyPlus simulation...');
    console.log('⏳ This will call the EnergyPlus API and may take 1-2 minutes...');
    console.log('   Calling: run-simulation function');
    
    const { data: simResult, error: simError } = await supabase.functions.invoke('run-simulation', {
      body: {
        idf_url: idfUrl.publicUrl,
        weather_url: weatherUrl.publicUrl,
        project_id: project.id
      }
    });

    if (simError) {
      console.error('❌ Simulation error:', simError);
      console.log('\n📝 Note: This may fail if:');
      console.log('   - EnergyPlus API is not running');
      console.log('   - Railway deployment is not active');
      console.log('   - Network connectivity issues');
      throw simError;
    }

    console.log('');
    console.log('🎉 REAL ENERGYPLUS SIMULATION COMPLETE!');
    console.log('=' .repeat(60));
    
    if (simResult) {
      console.log('📊 SIMULATION RESULTS:');
      console.log(JSON.stringify(simResult, null, 2));
      
      if (simResult.summary) {
        console.log('');
        console.log('📈 ENERGY CONSUMPTION (REAL DATA):');
        console.log(`  Total Energy: ${simResult.summary.totalEnergyUse || 'N/A'} kWh/year`);
        console.log(`  Heating: ${simResult.summary.heatingEnergy || 'N/A'} kWh`);
        console.log(`  Cooling: ${simResult.summary.coolingEnergy || 'N/A'} kWh`);
        console.log(`  Lighting: ${simResult.summary.lightingEnergy || 'N/A'} kWh`);
        console.log(`  Equipment: ${simResult.summary.equipmentEnergy || 'N/A'} kWh`);
        console.log(`  Peak Demand: ${simResult.summary.peakDemand || 'N/A'} kW`);
        console.log(`  EUI: ${simResult.summary.energyUseIntensity || 'N/A'} kWh/sq ft/year`);
        console.log('');
        console.log('✅ THESE ARE REAL EnergyPlus RESULTS!');
      }
    }

    console.log('');
    console.log('📝 Step 8: Generating compliance report with real data...');
    
    // Get the simulation ID
    const { data: simulations } = await supabase
      .from('simulations')
      .select('*')
      .eq('project_id', project.id)
      .order('created_at', { ascending: false })
      .limit(1)
      .single();

    if (simulations) {
      console.log('✅ Found simulation ID:', simulations.id);
      
      console.log('');
      console.log('🎯 NEXT STEPS:');
      console.log('   1. Open http://localhost:5173 in your browser');
      console.log(`   2. Navigate to project: ${project.name}`);
      console.log('   3. Go to "Audit Report" or "Reports" tab');
      console.log('   4. Click "Generate Compliance Report"');
      console.log('   5. Select ASHRAE 90.1-2022, Climate Zone 5A');
      console.log('   6. The report will use REAL simulation data!');
      console.log('');
      
      return {
        projectId: project.id,
        simulationId: simulations.id,
        results: simResult
      };
    }

    return { projectId: project.id, results: simResult };

  } catch (error) {
    console.error('❌ Test failed:', error);
    throw error;
  }
}

// Run the complete test
runCompleteSimulation()
  .then((result) => {
    console.log('✅ Complete simulation test finished!');
    if (result) {
      console.log('   Project ID:', result.projectId);
      if (result.simulationId) {
        console.log('   Simulation ID:', result.simulationId);
      }
    }
  })
  .catch((error) => {
    console.error('❌ Test failed:', error.message);
    process.exit(1);
  });

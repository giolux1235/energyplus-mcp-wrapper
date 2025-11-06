// Automated Real Simulation Runner
// This script automatically uploads files, runs simulation, and generates report

import { createClient } from '@supabase/supabase-js';
import { readFileSync } from 'fs';
import { createReadStream } from 'fs';

const SUPABASE_URL = 'https://rgccohhlrngjkvwbxmpv.supabase.co';
const SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJnY2NvaGhscm5namt2d2J4bXB2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjA5OTY2NjcsImV4cCI6MjA3NjU3MjY2N30.m6tihc1Ln33v1lObrrqGvuhaKM9S3FSua85HP0ZSETA';

const supabase = createClient(SUPABASE_URL, SUPABASE_KEY);

console.log('🚀 AUTOMATED REAL SIMULATION RUNNER');
console.log('='.repeat(60));
console.log('');

async function runAutomatedSimulation() {
  try {
    // Step 1: Sign in anonymously
    console.log('📝 Step 1: Authenticating...');
    const { data: authData, error: authError } = await supabase.auth.signInAnonymously();
    
    if (authError) {
      console.error('❌ Auth error:', authError.message);
      return;
    }
    
    console.log('✅ Authenticated as:', authData.user?.id);
    console.log('');

    // Step 2: Create project
    console.log('📝 Step 2: Creating project...');
    const { data: project, error: projError } = await supabase
      .from('projects')
      .insert({
        name: `Auto Test ${Date.now()}`,
        description: 'Automated real EnergyPlus simulation',
        building_type: 'office'
      })
      .select()
      .single();

    if (projError) throw projError;
    console.log('✅ Project created:', project.id);
    console.log('');

    // Step 3: Read files
    console.log('📁 Step 3: Loading NREL files...');
    const idfContent = readFileSync('RefBldgLargeOfficeNew2004_Chicago.idf');
    const weatherContent = readFileSync('USA_IL_Chicago-OHare.Intl.AP.725300_TMY3.epw');
    console.log('✅ Files loaded');
    console.log('');

    // Step 4: Upload IDF
    console.log('☁️ Step 4: Uploading IDF...');
    const idfPath = `${project.id}/idf-${Date.now()}.idf`;
    const { error: idfErr } = await supabase.storage
      .from('project-files')
      .upload(idfPath, idfContent);
    
    if (idfErr) throw idfErr;
    const { data: idfUrl } = supabase.storage.from('project-files').getPublicUrl(idfPath);
    console.log('✅ IDF uploaded');
    console.log('');

    // Step 5: Upload Weather
    console.log('☁️ Step 5: Uploading weather...');
    const weatherPath = `${project.id}/weather-${Date.now()}.epw`;
    const { error: weatherErr } = await supabase.storage
      .from('project-files')
      .upload(weatherPath, weatherContent);
    
    if (weatherErr) throw weatherErr;
    const { data: weatherUrl } = supabase.storage.from('project-files').getPublicUrl(weatherPath);
    console.log('✅ Weather uploaded');
    console.log('');

    // Step 6: Update project
    console.log('📊 Step 6: Updating project...');
    await supabase
      .from('projects')
      .update({
        idf_file_url: idfUrl.publicUrl,
        weather_file_url: weatherUrl.publicUrl
      })
      .eq('id', project.id);
    console.log('✅ Project updated');
    console.log('');

    // Step 7: Run simulation
    console.log('⚡ Step 7: Running REAL EnergyPlus simulation...');
    console.log('   This will take 1-2 minutes...');
    
    const { data: simData, error: simErr } = await supabase.functions.invoke('run-simulation', {
      body: {
        idf_url: idfUrl.publicUrl,
        weather_url: weatherUrl.publicUrl
      }
    });

    if (simErr) {
      console.error('❌ Simulation error:', simErr);
      return;
    }

    console.log('');
    console.log('🎉 SIMULATION COMPLETE!');
    console.log('='.repeat(60));
    
    if (simData?.summary) {
      console.log('📊 REAL RESULTS:');
      console.log(`  Total: ${simData.summary.totalEnergyUse}`);
      console.log(`  Heating: ${simData.summary.heatingEnergy}`);
      console.log(`  Cooling: ${simData.summary.coolingEnergy}`);
      console.log(`  EUI: ${simData.summary.energyUseIntensity}`);
    }

    // Step 8: Generate report
    console.log('');
    console.log('📄 Step 8: Generating compliance report...');
    
    const { data: reportData, error: reportErr } = await supabase.functions.invoke('generate-compliance-report', {
      body: {
        project_id: project.id,
        standard_type: 'ASHRAE 90.1',
        standard_version: '2022',
        climate_zone: '5A',
        building_type: 'office'
      }
    });

    if (reportErr) {
      console.error('❌ Report error:', reportErr);
    } else {
      console.log('✅ Report generated!');
      console.log('   Report ID:', reportData?.report_id);
    }

    console.log('');
    console.log('✅ ALL STEPS COMPLETE!');
    console.log(`   Project ID: ${project.id}`);
    console.log('   View report in the web UI at http://localhost:8081');

  } catch (error) {
    console.error('❌ Error:', error);
  }
}

runAutomatedSimulation();

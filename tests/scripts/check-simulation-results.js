// Check for real simulation results in Supabase
import { createClient } from '@supabase/supabase-js';

// You'll need to add these to your .env file
const supabaseUrl = process.env.VITE_SUPABASE_URL || 'https://your-project.supabase.co';
const supabaseKey = process.env.VITE_SUPABASE_ANON_KEY || 'your-anon-key';

const supabase = createClient(supabaseUrl, supabaseKey);

async function checkSimulationResults() {
  console.log('🔍 Checking for simulation results...\n');
  
  try {
    // Get latest simulations
    const { data: simulations, error } = await supabase
      .from('simulations')
      .select('*, projects(*)')
      .order('created_at', { ascending: false })
      .limit(5);
    
    if (error) throw error;
    
    if (!simulations || simulations.length === 0) {
      console.log('❌ No simulations found in database.');
      console.log('\n📝 To create simulations:');
      console.log('   1. Open http://localhost:8081 in browser');
      console.log('   2. Create a project');
      console.log('   3. Upload IDF and weather files');
      console.log('   4. Run simulation');
      return;
    }
    
    console.log(`✅ Found ${simulations.length} simulation(s):\n`);
    
    simulations.forEach((sim, idx) => {
      console.log(`Simulation ${idx + 1}:`);
      console.log(`  ID: ${sim.id}`);
      console.log(`  Project: ${sim.projects?.name || 'Unknown'}`);
      console.log(`  Status: ${sim.status}`);
      console.log(`  Data Source: ${sim.data_source || 'N/A'}`);
      console.log(`  Created: ${new Date(sim.created_at).toLocaleString()}`);
      
      if (sim.results && typeof sim.results === 'object') {
        console.log(`  Results: ${JSON.stringify(sim.results, null, 2)}`);
      }
      console.log('');
    });
    
    // Get latest projects
    const { data: projects } = await supabase
      .from('projects')
      .select('*')
      .order('created_at', { ascending: false })
      .limit(3);
    
    console.log(`\n📁 Latest Projects:\n`);
    projects?.forEach((proj, idx) => {
      console.log(`${idx + 1}. ${proj.name}`);
      console.log(`   IDF: ${proj.idf_file_url ? '✅ Yes' : '❌ No'}`);
      console.log(`   Weather: ${proj.weather_file_url ? '✅ Yes' : '❌ No'}`);
      console.log('');
    });
    
  } catch (error) {
    console.error('❌ Error:', error.message);
    console.log('\n📝 Make sure VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY are set in .env');
  }
}

checkSimulationResults();

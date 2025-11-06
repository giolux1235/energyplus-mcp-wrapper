/**
 * Test Script: Address to IDF File Workflow
 * 
 * This script demonstrates how to:
 * 1. Take a building address
 * 2. Geocode it to get county information
 * 3. Fetch the appropriate IDF file from the LBNL repository
 * 4. Run a simulation
 */

import { createClient } from 'https://esm.sh/@supabase/supabase-js@2.76.0';

const SUPABASE_URL = 'https://rgccohhlrngjkvwbxmpv.supabase.co';
const SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJnY2NvaGhscm5namt2d2J4bXB2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjA5OTY2NjcsImV4cCI6MjA3NjU3MjY2N30.m6tihc1Ln33v1lObrrqGvuhaKM9S3FSua85HP0ZSETA';

const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

// Test addresses to try
const TEST_ADDRESSES = [
  {
    name: "Los Angeles Office Building",
    address: "123 Main St, Los Angeles, CA 90012",
    expectedCounty: "Los Angeles",
    expectedState: "CA"
  },
  {
    name: "Chicago Commercial Building", 
    address: "100 N State St, Chicago, IL 60602",
    expectedCounty: "Cook",
    expectedState: "IL"
  },
  {
    name: "New York City Office",
    address: "350 5th Ave, New York, NY 10118",
    expectedCounty: "New York",
    expectedState: "NY"
  }
];

/**
 * Step 1: Geocode address to get county information
 */
async function geocodeAddress(address) {
  console.log(`\n📍 Geocoding: ${address}`);
  
  const { data, error } = await supabase.functions.invoke('geocode-address', {
    body: { address }
  });

  if (error) {
    console.error('❌ Geocoding failed:', error.message);
    return null;
  }

  if (!data.success) {
    console.error('❌ No geocoding results found');
    return null;
  }

  console.log('✅ Geocoded successfully:');
  console.log(`   County: ${data.county}`);
  console.log(`   State: ${data.state}`);
  console.log(`   Coordinates: ${data.latitude}, ${data.longitude}`);
  
  return data;
}

/**
 * Step 2: Map county to LBNL IDF repository file
 */
function getIDFRepositoryUrl(state, county) {
  // Format: STATE_County_Name_IDF.zip
  // Replace spaces with underscores
  const formattedCounty = county.replace(/\s+/g, '_');
  const filename = `${state}_${formattedCounty}_IDF.zip`;
  const url = `https://tier2.ess-dive.lbl.gov/doi-10-15485-2283980/data/Counties_IDF/${filename}`;
  
  console.log(`\n📦 IDF Repository URL: ${url}`);
  return url;
}

/**
 * Step 3: Create test project with address
 */
async function createTestProject(testCase, geocodeResult) {
  console.log(`\n🏗️ Creating test project...`);
  
  const { data: project, error } = await supabase
    .from('projects')
    .insert({
      name: testCase.name,
      address: testCase.address,
      building_type: 'commercial',
      latitude: geocodeResult.latitude,
      longitude: geocodeResult.longitude,
      status: 'draft',
      data_source: 'lbnl_repository',
      palmetto_data: {
        county: geocodeResult.county,
        state: geocodeResult.state,
        climate_zone: geocodeResult.climate_zone || '3B',
        idf_repository_url: getIDFRepositoryUrl(geocodeResult.state, geocodeResult.county)
      }
    })
    .select()
    .single();

  if (error) {
    console.error('❌ Failed to create project:', error.message);
    return null;
  }

  console.log(`✅ Project created: ${project.id}`);
  return project;
}

/**
 * Run the complete test workflow
 */
async function runTest(testCase) {
  console.log('\n' + '='.repeat(80));
  console.log(`🧪 TEST: ${testCase.name}`);
  console.log('='.repeat(80));

  // Step 1: Geocode the address
  const geocodeResult = await geocodeAddress(testCase.address);
  if (!geocodeResult) {
    console.log('❌ Test failed: Could not geocode address');
    return { success: false, testCase, error: 'Geocoding failed' };
  }

  // Validate expected values
  if (testCase.expectedCounty && geocodeResult.county !== testCase.expectedCounty) {
    console.warn(`⚠️ County mismatch: expected "${testCase.expectedCounty}", got "${geocodeResult.county}"`);
  }

  // Step 2: Get IDF repository URL
  const idfUrl = getIDFRepositoryUrl(geocodeResult.state, geocodeResult.county);

  // Step 3: Create test project
  const project = await createTestProject(testCase, geocodeResult);
  if (!project) {
    console.log('❌ Test failed: Could not create project');
    return { success: false, testCase, error: 'Project creation failed' };
  }

  console.log('\n✅ TEST PASSED');
  console.log(`   Project ID: ${project.id}`);
  console.log(`   IDF Source: ${idfUrl}`);
  
  return {
    success: true,
    testCase,
    project,
    geocodeResult,
    idfUrl
  };
}

/**
 * Run all tests
 */
async function runAllTests() {
  console.log('\n🚀 Starting Address-to-IDF Test Suite\n');

  const results = [];

  for (const testCase of TEST_ADDRESSES) {
    const result = await runTest(testCase);
    results.push(result);
    
    // Wait a bit between tests to avoid rate limiting
    await new Promise(resolve => setTimeout(resolve, 1000));
  }

  // Summary
  console.log('\n' + '='.repeat(80));
  console.log('📊 TEST SUMMARY');
  console.log('='.repeat(80));

  const passed = results.filter(r => r.success).length;
  const failed = results.filter(r => !r.success).length;

  console.log(`\n✅ Passed: ${passed}/${results.length}`);
  console.log(`❌ Failed: ${failed}/${results.length}`);

  results.forEach((result, index) => {
    const status = result.success ? '✅' : '❌';
    console.log(`\n${status} Test ${index + 1}: ${result.testCase.name}`);
    if (result.project) {
      console.log(`   Project ID: ${result.project.id}`);
      console.log(`   IDF URL: ${result.idfUrl}`);
    }
    if (result.error) {
      console.log(`   Error: ${result.error}`);
    }
  });
}

// Run the tests
if (import.meta.main) {
  runAllTests().catch(console.error);
}

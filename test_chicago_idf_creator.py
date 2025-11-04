#!/usr/bin/env python3
"""
Test simulation with a random Chicago address using IDF creator service
"""

import requests
import json
import os
import random

# Configuration
IDF_CREATOR_URL = "https://web-production-3092c.up.railway.app"
LOCAL_ENERGYPLUS_API = "http://localhost:8080"
WEATHER_FILE = "test-chicago-weather.epw"

# Random Chicago addresses
CHICAGO_ADDRESSES = [
    "123 N Michigan Ave, Chicago, IL 60601",
    "456 W Wacker Dr, Chicago, IL 60606",
    "789 S State St, Chicago, IL 60605",
    "321 E Randolph St, Chicago, IL 60601",
    "654 N LaSalle Dr, Chicago, IL 60610",
    "987 W Chicago Ave, Chicago, IL 60622",
    "147 S Dearborn St, Chicago, IL 60603",
    "258 N Clark St, Chicago, IL 60610",
    "369 E Lake St, Chicago, IL 60601",
    "741 W Monroe St, Chicago, IL 60661"
]

def read_weather_file():
    """Read weather file content"""
    if os.path.exists(WEATHER_FILE):
        with open(WEATHER_FILE, 'r') as f:
            return f.read()
    else:
        print(f"❌ Weather file not found: {WEATHER_FILE}")
        return None

def get_idf_from_creator(address):
    """Get IDF from creator service using Chicago address"""
    print("=" * 60)
    print("STEP 1: Getting IDF from Creator Service")
    print("=" * 60)
    print(f"📍 Address: {address}")
    
    # First, check if service is up
    try:
        health_url = f"{IDF_CREATOR_URL}/health"
        print(f"\n📡 Checking health: {health_url}")
        response = requests.get(health_url, timeout=10)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            health_data = response.json()
            print(f"   ✅ Service is healthy: {health_data.get('status', 'unknown')}")
    except Exception as e:
        print(f"   ⚠️  Health check failed: {e}")
        print(f"   Continuing anyway...")
    
    # Try to get an IDF with the address
    test_request = {
        "address": address,
        "building_type": "office",
        "floor_area": 500,
        "num_floors": 2
    }
    
    try:
        url = f"{IDF_CREATOR_URL}/generate"
        print(f"\n📡 POST {url}")
        print(f"   Payload: {json.dumps(test_request, indent=2)}")
        
        response = requests.post(url, json=test_request, timeout=30)
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"   ✅ Success!")
                print(f"   Response keys: {list(data.keys())}")
                
                # Extract IDF content - try multiple possible fields
                idf_content = None
                for field in ['idf_content', 'idf', 'content', 'file', 'idf_file', 'data']:
                    if field in data:
                        idf_content = data[field]
                        print(f"   ✅ Found '{field}' field")
                        break
                
                # If we got a filename but no content, try to download it
                if not idf_content and 'filename' in data:
                    filename = data['filename']
                    print(f"   📄 Got filename: {filename}")
                    print(f"   📥 Downloading IDF file...")
                    
                    # Try different download endpoints
                    download_endpoints = [
                        f"/download/{filename}",
                        f"/files/{filename}",
                        f"/idf/{filename}",
                        f"/{filename}"
                    ]
                    
                    for endpoint in download_endpoints:
                        try:
                            download_url = f"{IDF_CREATOR_URL}{endpoint}"
                            print(f"   📥 Trying: {download_url}")
                            dl_response = requests.get(download_url, timeout=10)
                            if dl_response.status_code == 200:
                                if 'Version' in dl_response.text or 'Building' in dl_response.text:
                                    idf_content = dl_response.text
                                    print(f"   ✅ Successfully downloaded IDF from {endpoint}")
                                    break
                            else:
                                print(f"      Status: {dl_response.status_code}")
                        except Exception as e:
                            print(f"      Error: {e}")
                
                if idf_content:
                    # Handle different response types
                    if isinstance(idf_content, str):
                        idf_text = idf_content
                    elif isinstance(idf_content, dict):
                        # Try to extract content from nested structure
                        idf_text = idf_content.get('content', str(idf_content))
                    else:
                        idf_text = str(idf_content)
                    
                    print(f"   📄 IDF content length: {len(idf_text)} bytes")
                    
                    # Verify it looks like an IDF
                    if 'Version' in idf_text or 'Building' in idf_text or 'Site:Location' in idf_text:
                        print(f"   ✅ Valid IDF content detected")
                        
                        # Save IDF for inspection
                        with open('chicago_test_idf.idf', 'w') as f:
                            f.write(idf_text)
                        print(f"   💾 Saved to: chicago_test_idf.idf")
                        
                        if 'parameters' in data:
                            print(f"   📋 Parameters: {data.get('parameters', {})}")
                        
                        return idf_text
                    else:
                        print(f"   ⚠️  Content doesn't look like IDF")
                        print(f"   Preview: {idf_text[:300]}")
                else:
                    print(f"   ⚠️  No IDF content found")
                    print(f"   Full response: {json.dumps(data, indent=2)[:800]}")
            except json.JSONDecodeError:
                # Maybe it's plain text (the IDF itself)
                if len(response.text) > 1000:
                    if 'Version' in response.text or 'Building' in response.text:
                        print(f"   ✅ Got IDF as plain text, length: {len(response.text)} bytes")
                        with open('chicago_test_idf.idf', 'w') as f:
                            f.write(response.text)
                        return response.text
                    else:
                        print(f"   ⚠️  Response is text but doesn't look like IDF")
                        print(f"   Preview: {response.text[:300]}")
        else:
            print(f"   ❌ Error response: {response.text[:500]}")
            return None
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None

def run_simulation(idf_content, weather_content):
    """Run simulation using local EnergyPlus API"""
    print("\n" + "=" * 60)
    print("STEP 2: Running EnergyPlus Simulation")
    print("=" * 60)
    
    # Check health first
    try:
        print(f"📡 Checking local API health: {LOCAL_ENERGYPLUS_API}/healthz")
        response = requests.get(f"{LOCAL_ENERGYPLUS_API}/healthz", timeout=5)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            health_data = response.json()
            print(f"   ✅ API is healthy: {health_data.get('status', 'unknown')}")
    except Exception as e:
        print(f"   ❌ Local API not responding: {e}")
        print(f"   Make sure the API is running on {LOCAL_ENERGYPLUS_API}")
        return None
    
    # Send simulation request
    payload = {
        "idf_content": idf_content,
        "weather_content": weather_content
    }
    
    print(f"\n📊 Sending simulation request...")
    print(f"   IDF size: {len(idf_content)} bytes")
    print(f"   Weather size: {len(weather_content)} bytes")
    
    try:
        print(f"\n⏳ Running simulation (this may take a few minutes)...")
        response = requests.post(
            f"{LOCAL_ENERGYPLUS_API}/simulate",
            json=payload,
            timeout=600  # 10 minutes for simulation
        )
        
        print(f"\n   Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"\n✅ Simulation completed!")
            print(f"   Simulation status: {result.get('simulation_status', 'unknown')}")
            
            # Check for energy results
            if 'energy_results' in result:
                energy = result['energy_results']
                print(f"\n📊 ENERGY RESULTS:")
                print(f"   Total Site Energy: {energy.get('total_site_energy_kwh', 'N/A')} kWh")
                print(f"   Building Area: {energy.get('building_area_m2', 'N/A')} m²")
                print(f"   EUI: {energy.get('eui_kwh_m2', 'N/A')} kWh/m²")
                if 'electricity_kwh' in energy:
                    print(f"   Electricity: {energy.get('electricity_kwh', 'N/A')} kWh")
                if 'natural_gas_kwh' in energy:
                    print(f"   Natural Gas: {energy.get('natural_gas_kwh', 'N/A')} kWh")
            else:
                print(f"\n⚠️  No energy_results in response")
                print(f"   Available keys: {list(result.keys())}")
            
            # Check for total energy consumption
            if 'total_energy_consumption' in result:
                print(f"\n📊 Total Energy Consumption: {result['total_energy_consumption']} kWh")
            
            # Check for errors
            if 'error_message' in result:
                print(f"\n❌ ERROR: {result['error_message']}")
            
            # Check for warnings
            if 'warnings' in result and result['warnings']:
                print(f"\n⚠️  WARNINGS ({len(result['warnings'])}):")
                for warning in result['warnings'][:5]:
                    print(f"   - {warning}")
            
            # Save full result for inspection
            with open('chicago_test_result.json', 'w') as f:
                json.dump(result, f, indent=2)
            print(f"\n💾 Full result saved to: chicago_test_result.json")
            
            return result
        else:
            print(f"❌ Error response: {response.text[:500]}")
            return None
            
    except requests.exceptions.Timeout:
        print(f"❌ Request timed out (simulation took > 10 minutes)")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    print("🏙️  Testing Chicago Building Simulation with IDF Creator")
    print("=" * 60)
    
    # Pick a random Chicago address
    address = random.choice(CHICAGO_ADDRESSES)
    print(f"\n🎲 Selected random address: {address}")
    
    # Step 1: Get IDF from creator
    idf_content = get_idf_from_creator(address)
    
    if not idf_content:
        print("\n❌ Could not get IDF from creator service")
        print("   The service may not be fixed yet or there's a connection issue.")
        return
    
    # Step 2: Read weather file
    print("\n" + "=" * 60)
    print("STEP 2: Reading Weather File")
    print("=" * 60)
    weather_content = read_weather_file()
    if not weather_content:
        print("\n❌ Could not read weather file")
        return
    
    print(f"   ✅ Weather file loaded: {len(weather_content)} bytes")
    
    # Step 3: Run simulation
    result = run_simulation(idf_content, weather_content)
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    if result:
        if 'energy_results' in result or result.get('total_energy_consumption', 0) > 0:
            print("✅ SUCCESS - Simulation completed with energy results!")
            print(f"📍 Address used: {address}")
            print(f"🌤️  Weather file: {WEATHER_FILE}")
        else:
            print("⚠️  Simulation completed but no energy results found")
            print("   Check chicago_test_result.json for details")
    else:
        print("❌ Simulation failed")
        print("   Check the output above for error details")

if __name__ == "__main__":
    main()


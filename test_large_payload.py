#!/usr/bin/env python3
"""
Test Large Payload Handling
"""

import json
import subprocess
import sys

def create_large_idf():
    """Create a large IDF content to test payload handling"""
    large_idf = 'Building,Test Building,0.0,City,0.04,0.4,FullInteriorAndExterior,25,6;\n'
    large_idf += 'Site:Location,Test Location,40.0,-74.0,-5.0,10.0;\n'
    large_idf += 'Zone,MainZone,0.0,0.0,0.0,0.0,1,1,autocalculate,autocalculate;\n'
    large_idf += 'ZoneArea,MainZone,1000.0;\n'
    
    # Add many objects to simulate a large file
    for i in range(1000):
        large_idf += f'Lights,Lighting{i},MainZone,Schedule1,LightingLevel,100.0,0.0,0.0,0.0,0.0;\n'
        large_idf += f'ElectricEquipment,Equipment{i},MainZone,Schedule1,EquipmentLevel,50.0,0.0,0.0,0.0,0.0;\n'
        large_idf += f'People,People{i},MainZone,Schedule1,People,1.0,0.0,0.0,0.0,0.0;\n'
    
    return large_idf

def test_large_payload():
    """Test the Railway API with large payload"""
    print("=== TESTING LARGE PAYLOAD HANDLING ===")
    
    # Create large IDF content
    large_idf = create_large_idf()
    print(f"Generated large IDF: {len(large_idf)} bytes")
    print(f"First 200 chars: {large_idf[:200]}")
    print(f"Last 200 chars: {large_idf[-200:]}")
    
    # Create payload
    payload = {
        'content_type': 'idf',
        'idf_content': large_idf
    }
    
    # Convert to JSON
    json_payload = json.dumps(payload)
    print(f"JSON payload size: {len(json_payload)} bytes")
    
    # Test with curl
    try:
        print("\n=== SENDING TO RAILWAY API ===")
        result = subprocess.run([
            'curl', '-X', 'POST', 
            '-H', 'Content-Type: application/json',
            '-d', json_payload,
            'https://web-production-1d1be.up.railway.app/simulate'
        ], capture_output=True, text=True, timeout=60)
        
        print(f"Status Code: {result.returncode}")
        print(f"Response Length: {len(result.stdout)} bytes")
        
        if result.returncode == 0:
            try:
                response_data = json.loads(result.stdout)
                print(f"✅ SUCCESS: API responded")
                print(f"Version: {response_data.get('version', 'Unknown')}")
                print(f"Content Size: {response_data.get('content_size', 'NOT FOUND')} bytes")
                print(f"Building Area: {response_data.get('building_area', 'NOT FOUND')} m²")
                print(f"Total Energy: {response_data.get('total_energy_consumption', 'NOT FOUND')} kWh")
                print(f"Lighting Objects: {response_data.get('lighting_objects_found', 'NOT FOUND')}")
                print(f"Equipment Objects: {response_data.get('equipment_objects_found', 'NOT FOUND')}")
                print(f"Railway Optimized: {response_data.get('railway_optimized', False)}")
                print(f"Error: {response_data.get('error', 'None')}")
                
                # Check if content was truncated
                if response_data.get('content_size', 0) < len(large_idf):
                    print(f"⚠️  WARNING: Content was truncated!")
                    print(f"   Sent: {len(large_idf)} bytes")
                    print(f"   Received: {response_data.get('content_size', 0)} bytes")
                else:
                    print(f"✅ SUCCESS: Full content processed!")
                    
            except json.JSONDecodeError as e:
                print(f"❌ JSON Parse Error: {e}")
                print(f"Response: {result.stdout[:500]}")
        else:
            print(f"❌ CURL Error: {result.stderr}")
            
    except subprocess.TimeoutExpired:
        print("❌ TIMEOUT: Request took too long")
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")

if __name__ == '__main__':
    test_large_payload()

#!/usr/bin/env python3
import requests
import json
import time

def test_api():
    url = "https://web-production-1d1be.up.railway.app/simulate"
    
    # Test 1: Small file
    print("=== TEST 1: Small File ===")
    small_payload = {
        "content_type": "idf",
        "idf_content": "Building,Test Building,0.0,City,0.04,0.4,FullInteriorAndExterior,25,6;\nZone,MainZone,0.0,0.0,0.0,0.0,1,1,autocalculate,autocalculate;\nZoneArea,MainZone,1000.0;"
    }
    
    try:
        response = requests.post(url, json=small_payload, timeout=60)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Small file success: {data.get('simulation_status')}")
            print(f"Building area: {data.get('building_area', 'N/A')}")
            if data.get('simulation_status') == 'error':
                print(f"Error message: {data.get('error_message', 'No error message')}")
        else:
            print(f"❌ Small file failed: {response.text}")
    except Exception as e:
        print(f"❌ Small file error: {e}")
    
    print("\n=== TEST 2: Medium File ===")
    # Test 2: Medium file (create larger IDF)
    medium_idf = "Building,Test Building,0.0,City,0.04,0.4,FullInteriorAndExterior,25,6;\n"
    for i in range(100):
        medium_idf += f"Zone,Zone{i},0.0,0.0,0.0,0.0,1,1,autocalculate,autocalculate;\n"
        medium_idf += f"ZoneArea,Zone{i},100.0;\n"
    
    medium_payload = {
        "content_type": "idf", 
        "idf_content": medium_idf
    }
    
    try:
        response = requests.post(url, json=medium_payload, timeout=60)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Medium file success: {data.get('simulation_status')}")
            print(f"Building area: {data.get('building_area', 'N/A')}")
        else:
            print(f"❌ Medium file failed: {response.text}")
    except Exception as e:
        print(f"❌ Medium file error: {e}")
    
    print("\n=== TEST 3: Large File ===")
    # Test 3: Large file (create very large IDF)
    large_idf = "Building,Test Building,0.0,City,0.04,0.4,FullInteriorAndExterior,25,6;\n"
    for i in range(1000):
        large_idf += f"Zone,Zone{i},0.0,0.0,0.0,0.0,1,1,autocalculate,autocalculate;\n"
        large_idf += f"ZoneArea,Zone{i},100.0;\n"
        large_idf += f"Lights,Light{i},Zone{i},LightingSchedule,WattsPerZoneFloorArea,10.0,0.0,0.0,0.0;\n"
        large_idf += f"ElectricEquipment,Equipment{i},Zone{i},EquipmentSchedule,WattsPerZoneFloorArea,5.0,0.0,0.0,0.0;\n"
    
    large_payload = {
        "content_type": "idf",
        "idf_content": large_idf
    }
    
    try:
        response = requests.post(url, json=large_payload, timeout=120)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Large file success: {data.get('simulation_status')}")
            print(f"Building area: {data.get('building_area', 'N/A')}")
        else:
            print(f"❌ Large file failed: {response.text}")
    except Exception as e:
        print(f"❌ Large file error: {e}")

if __name__ == "__main__":
    test_api()

#!/usr/bin/env python3
import requests
import json

def test_with_real_idf():
    url = "https://web-production-1d1be.up.railway.app/simulate"
    
    # Create a minimal but valid IDF file
    idf_content = """
Version,23.2;

Building,
  Simple Building,         !- Name
  0.0,                     !- North Axis {deg}
  City,                    !- Terrain
  0.04,                    !- Loads Convergence Tolerance Value
  0.4,                     !- Temperature Convergence Tolerance Value {deltaC}
  FullInteriorAndExterior, !- Solar Distribution
  25,                      !- Maximum Number of Warmup Days
  6;                       !- Minimum Number of Warmup Days

Timestep,4;

GlobalGeometryRules,
  UpperLeftCorner,         !- Starting Vertex Position
  CounterClockWise,        !- Vertex Entry Direction
  Relative;                !- Coordinate System

Zone,
  Main Zone,               !- Name
  0.0,                     !- Direction of Relative North {deg}
  0.0,                     !- X Origin {m}
  0.0,                     !- Y Origin {m}
  0.0,                     !- Z Origin {m}
  1,                       !- Type
  1,                       !- Multiplier
  autocalculate,           !- Ceiling Height {m}
  autocalculate;           !- Volume {m3}

BuildingSurface:Detailed,
  Floor,                   !- Name
  Floor,                   !- Surface Type
  FLOOR,                   !- Construction Name
  Main Zone,               !- Zone Name
  Ground,                  !- Outside Boundary Condition
  ,                        !- Outside Boundary Condition Object
  NoSun,                   !- Sun Exposure
  NoWind,                  !- Wind Exposure
  1.0,                     !- View Factor to Ground
  4,                       !- Number of Vertices
  0.0,0.0,0.0,            !- X,Y,Z ==> Vertex 1 {m}
  10.0,0.0,0.0,           !- X,Y,Z ==> Vertex 2 {m}
  10.0,10.0,0.0,          !- X,Y,Z ==> Vertex 3 {m}
  0.0,10.0,0.0;           !- X,Y,Z ==> Vertex 4 {m}

Construction,
  FLOOR,                   !- Name
  C5 - 4 IN HW CONCRETE;   !- Outside Layer

Material,
  C5 - 4 IN HW CONCRETE,   !- Name
  MediumRough,             !- Roughness
  0.1014984,               !- Thickness {m}
  1.729577,                !- Conductivity {W/m-K}
  2242.585,                !- Density {kg/m3}
  836.8000,                !- Specific Heat {J/kg-K}
  0.9000000,               !- Thermal Absorptance
  0.6500000,               !- Solar Absorptance
  0.6500000;               !- Visible Absorptance
"""
    
    payload = {
        "content_type": "idf",
        "idf_content": idf_content
    }
    
    print("=== TESTING WITH VALID IDF FILE ===")
    print(f"IDF size: {len(idf_content)} bytes")
    
    try:
        response = requests.post(url, json=payload, timeout=120)
        print(f"\nStatus: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"\nSimulation Status: {data.get('simulation_status')}")
            print(f"Version: {data.get('version')}")
            print(f"EnergyPlus Version: {data.get('energyplus_version')}")
            
            if data.get('simulation_status') == 'error':
                print(f"\n❌ Error: {data.get('error_message', 'No error message')}")
            else:
                print(f"\n✅ SUCCESS!")
                print(f"\n📊 ENERGY DATA:")
                print(f"Total Energy: {data.get('total_energy_consumption', 'N/A')}")
                print(f"Heating Energy: {data.get('heating_energy', 'N/A')}")
                print(f"Cooling Energy: {data.get('cooling_energy', 'N/A')}")
                print(f"Lighting Energy: {data.get('lighting_energy', 'N/A')}")
                print(f"Equipment Energy: {data.get('equipment_energy', 'N/A')}")
                print(f"Building Area: {data.get('building_area', 'N/A')}")
                print(f"Energy Intensity: {data.get('energy_intensity', 'N/A')}")
                print(f"Peak Demand: {data.get('peak_demand', 'N/A')}")
                
                if data.get('using_fallback_data'):
                    print(f"\n⚠️ WARNING: Using fallback mock data!")
                    print(f"Warning: {data.get('warning', 'N/A')}")
                else:
                    print(f"\n✅ Using REAL EnergyPlus simulation data!")
                
        else:
            print(f"❌ Failed: {response.text}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_with_real_idf()

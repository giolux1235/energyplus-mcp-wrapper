#!/usr/bin/env python3
"""
Test Railway API with measured energy data (simulated bills)
"""

import requests
import json
import os

# Railway API endpoint
API_URL = "https://web-production-1d1be.up.railway.app/simulate"

# Read the Medium Office file from Desktop
idf_path = os.path.expanduser("~/Desktop/MediumOffice.idf")
weather_path = os.path.expanduser("~/Desktop/Chicago.epw")

print("🧪 Testing Measured Data Comparison Feature")
print("="*100)

# Read IDF and weather files
with open(idf_path, 'r') as f:
    idf_content = f.read()

with open(weather_path, 'r') as f:
    weather_content = f.read()

# Simulate measured data from real bills
# This represents actual electricity consumption from utility bills
measured_data = {
    "total_annual_kwh": 150000,  # Annual total from bills
    "year": 2024,
    "monthly": [
        {"month": 1, "kwh": 12000},   # January
        {"month": 2, "kwh": 10000},   # February
        {"month": 3, "kwh": 9500},    # March
        {"month": 4, "kwh": 8500},    # April
        {"month": 5, "kwh": 8000},    # May
        {"month": 6, "kwh": 12000},   # June
        {"month": 7, "kwh": 15000},   # July (hot summer, AC)
        {"month": 8, "kwh": 14000},   # August
        {"month": 9, "kwh": 10000},   # September
        {"month": 10, "kwh": 9000},   # October
        {"month": 11, "kwh": 11000},  # November
        {"month": 12, "kwh": 13000}   # December
    ]
}

# Prepare request
payload = {
    "idf_content": idf_content,
    "weather_content": weather_content,
    "measured_data": measured_data
}

print("\n📊 Request Details:")
print(f"   IDF: {len(idf_content)} bytes")
print(f"   Weather: {len(weather_content)} bytes")
print(f"   Measured Energy: {measured_data['total_annual_kwh']:,} kWh")
print(f"   Monthly data: {len(measured_data['monthly'])} months")

# Call API
print("\n🚀 Calling Railway API...")
response = requests.post(API_URL, json=payload, timeout=120)

if response.status_code == 200:
    result = response.json()
    
    print("\n" + "="*100)
    print("✅ ✅ ✅ API RESPONSE ✅ ✅ ✅")
    print("="*100)
    
    # Print simulation results
    if result.get('simulation_status') == 'success':
        print("\n📊 SIMULATION RESULTS:")
        print(f"   Total Energy: {result.get('total_energy_consumption', 0):,.0f} kWh/year")
        print(f"   Building Area: {result.get('building_area', 0):,.2f} m²")
        print(f"   Energy Intensity: {result.get('total_energy_consumption', 0) / max(result.get('building_area', 1), 1):.2f} kWh/m²/year")
        
        # Print validation results
        validation = result.get('validation', {})
        if validation:
            print("\n🔍 VALIDATION AGAINST MEASURED DATA:")
            print(f"   Status: {validation.get('status', 'N/A')}")
            print(f"   Simulated: {validation.get('simulated_total_kwh', 0):,.0f} kWh")
            print(f"   Measured: {validation.get('measured_total_kwh', 0):,.0f} kWh")
            print(f"   Difference: {validation.get('difference_kwh', 0):,.0f} kWh ({validation.get('difference_percent', 0):.1f}%)")
            print(f"   Calibration: {validation.get('calibration_status', 'N/A')}")
            
            if validation.get('has_monthly_data'):
                print(f"   Monthly Data: {validation.get('months_provided', 0)} months provided")
        
        # Print recommendations
        recommendations = result.get('recommendations', [])
        if recommendations:
            print("\n💡 RECOMMENDATIONS:")
            for i, rec in enumerate(recommendations, 1):
                print(f"   {i}. {rec}")
        
        # Print energy breakdown
        print("\n📋 ENERGY BREAKDOWN:")
        print(f"   🔥 Heating:      {result.get('heating_energy', 0):>10,.0f} kWh")
        print(f"   ❄️  Cooling:      {result.get('cooling_energy', 0):>10,.0f} kWh")
        print(f"   💡 Lighting:     {result.get('lighting_energy', 0):>10,.0f} kWh")
        print(f"   💻 Equipment:    {result.get('equipment_energy', 0):>10,.0f} kWh")
        print(f"   🌪️  Fans:         {result.get('fans_energy', 0):>10,.0f} kWh")
        print(f"   🚿 Pumps:        {result.get('pumps_energy', 0):>10,.0f} kWh")
    
    else:
        print(f"\n❌ Simulation failed: {result.get('error_message', 'Unknown error')}")
    
    # Print full JSON for inspection
    print("\n" + "="*100)
    print("📄 FULL JSON RESPONSE:")
    print("="*100)
    print(json.dumps(result, indent=2))

else:
    print(f"\n❌ API Error: {response.status_code}")
    print(f"Response: {response.text[:500]}")


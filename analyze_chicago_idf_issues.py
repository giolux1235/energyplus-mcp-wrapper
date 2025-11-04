#!/usr/bin/env python3
"""
Analyze IDF and energy results for issues and incoherences
"""

import json

# Chicago coordinates
CHICAGO_LAT = 41.98
CHICAGO_LON = -87.92
CHICAGO_TZ = -6.0

# Expected EUI ranges for office buildings
MIN_EUI_OFFICE = 50  # kWh/m²/year (very low)
MAX_EUI_OFFICE = 300  # kWh/m²/year (high)
TYPICAL_EUI_OFFICE = 100-150  # kWh/m²/year

print("=" * 70)
print("IDF CREATOR SERVICE - ANALYSIS OF ISSUES AND INCOHERENCES")
print("=" * 70)

# Read results
with open('chicago_test_result.json', 'r') as f:
    result = json.load(f)

# Read IDF location
idf_location = None
with open('chicago_test_idf.idf', 'r') as f:
    for line in f:
        if 'Site:Location' in line:
            # Read next few lines
            lines = [line]
            for _ in range(5):
                lines.append(f.readline())
            idf_content = ''.join(lines)
            break

print("\n1. LOCATION ANALYSIS")
print("-" * 70)

# Extract location from IDF
if idf_content:
    # Parse Site:Location
    import re
    lat_match = re.search(r'(\d+\.\d+),.*!- Latitude', idf_content)
    lon_match = re.search(r'(\-?\d+\.\d+),.*!- Longitude', idf_content)
    tz_match = re.search(r'(\-?\d+\.\d+),.*!- Time Zone', idf_content)
    
    if lat_match and lon_match:
        idf_lat = float(lat_match.group(1))
        idf_lon = float(lon_match.group(1))
        idf_tz = float(tz_match.group(1)) if tz_match else None
        
        print(f"IDF Location (from file):")
        print(f"  Latitude:  {idf_lat}°")
        print(f"  Longitude: {idf_lon}°")
        print(f"  Time Zone: {idf_tz}°")
        print()
        print(f"Expected Chicago Location:")
        print(f"  Latitude:  {CHICAGO_LAT}°")
        print(f"  Longitude: {CHICAGO_LON}°")
        print(f"  Time Zone: {CHICAGO_TZ}°")
        print()
        
        lat_diff = abs(idf_lat - CHICAGO_LAT)
        lon_diff = abs(idf_lon - CHICAGO_LON)
        
        if lat_diff > 1 or lon_diff > 1:
            print("❌ CRITICAL: Location mismatch!")
            print(f"   Latitude difference: {lat_diff:.2f}°")
            print(f"   Longitude difference: {lon_diff:.2f}°")
            print(f"   This location ({idf_lat}, {idf_lon}) is NOT Chicago!")
            if idf_lat > 40 and idf_lat < 50 and idf_lon > 0 and idf_lon < 10:
                print(f"   This appears to be in Europe (possibly Italy/France)")
            print()
            print("   Impact: Weather file location was used instead (good!),")
            print("   but the IDF location data is incorrect.")
        else:
            print("✅ Location matches Chicago")

print("\n2. BUILDING AREA ANALYSIS")
print("-" * 70)

# Check CSV data
csv_data = result.get('csv_previews', {}).get('eplustbl.csv', {}).get('lines', [])
csv_area = None
for i, line in enumerate(csv_data):
    if 'Total Building Area' in line and '[m2]' in line:
        # Next line should have the value
        if i + 1 < len(csv_data):
            parts = csv_data[i+1].split(',')
            if len(parts) >= 2:
                try:
                    csv_area = float(parts[-1].strip())
                except:
                    pass

reported_area = result.get('building_area', 0)
csv_area_from_energy = None

# Also check from energy per area
for line in csv_data:
    if 'Total Site Energy' in line and 'Energy Per Total Building Area' in line:
        parts = line.split(',')
        if len(parts) >= 3:
            try:
                # Energy per area is in MJ/m²
                energy_per_area_mj = float(parts[2].strip())
                # Convert to kWh/m²
                energy_per_area_kwh = energy_per_area_mj / 3.6
                # Get total energy from next line
                if 'Total Site Energy' in csv_data[csv_data.index(line) + 1]:
                    total_energy_line = csv_data[csv_data.index(line) + 1]
                    energy_parts = total_energy_line.split(',')
                    if len(energy_parts) >= 2:
                        total_energy_gj = float(energy_parts[2].strip())
                        csv_area_from_energy = (total_energy_gj * 277.778) / energy_per_area_kwh
            except:
                pass

print(f"Reported Building Area (from API): {reported_area:.2f} m²")
if csv_area:
    print(f"CSV Building Area:                 {csv_area:.2f} m²")
    if abs(reported_area - csv_area) > 1:
        print(f"❌ Area mismatch: {abs(reported_area - csv_area):.2f} m² difference")
        print(f"   This suggests the API is using a different area calculation")
    else:
        print("✅ Areas match")
else:
    print("⚠️  Could not extract area from CSV")

print("\n3. ENERGY CONSUMPTION ANALYSIS")
print("-" * 70)

# Get energy from CSV
csv_energy_gj = None
csv_energy_kwh = None

for line in csv_data:
    if 'Total Site Energy' in line and 'GJ' in line:
        parts = line.split(',')
        if len(parts) >= 2:
            try:
                csv_energy_gj = float(parts[2].strip())
                csv_energy_kwh = csv_energy_gj * 277.778  # Convert GJ to kWh
            except:
                pass

reported_energy = result.get('total_energy_consumption', 0)
reported_eui = result.get('energy_intensity', 0)

print(f"Reported Total Energy (from API): {reported_energy:.2f} kWh")
if csv_energy_kwh:
    print(f"CSV Total Energy:                  {csv_energy_kwh:.2f} kWh ({csv_energy_gj:.2f} GJ)")
    energy_diff = abs(reported_energy - csv_energy_kwh)
    energy_diff_pct = (energy_diff / csv_energy_kwh) * 100 if csv_energy_kwh > 0 else 0
    
    if energy_diff > 100:
        print(f"❌ CRITICAL: Energy mismatch!")
        print(f"   Difference: {energy_diff:.2f} kWh ({energy_diff_pct:.1f}%)")
        print(f"   The API is reporting {energy_diff_pct:.1f}% less energy than the CSV!")
        print(f"   This is a MAJOR discrepancy that needs investigation.")
    else:
        print("✅ Energy values match")
else:
    print("⚠️  Could not extract energy from CSV")

print(f"\nReported EUI: {reported_eui:.2f} kWh/m²/year")
if csv_energy_kwh and csv_area:
    csv_eui = csv_energy_kwh / csv_area
    print(f"CSV EUI:     {csv_eui:.2f} kWh/m²/year")
    
    if csv_eui < MIN_EUI_OFFICE:
        print(f"⚠️  EUI is very low for an office building (typical: 100-150 kWh/m²/year)")
    elif csv_eui > MAX_EUI_OFFICE:
        print(f"⚠️  EUI is very high for an office building (typical: 100-150 kWh/m²/year)")
    else:
        print(f"✅ EUI is within typical range for office buildings")

print("\n4. GEOMETRY ISSUES")
print("-" * 70)

warnings = result.get('warnings', [])
geometry_warnings = [w for w in warnings if 'Volume' in w or 'upside down' in w or 'Floor' in w or 'Ceiling' in w]

if geometry_warnings:
    print(f"❌ Found {len(geometry_warnings)} geometry-related warnings:")
    print("   - Negative zone volumes (zones calculated as upside down)")
    print("   - Floors and ceilings with incorrect tilt angles")
    print("   - These issues can affect energy calculations")
else:
    print("✅ No major geometry warnings")

print("\n5. HVAC SYSTEM ISSUES")
print("-" * 70)

hvac_warnings = [w for w in warnings if 'DX' in w or 'Coil' in w or 'VAV' in w or 'flow rate' in w]

if hvac_warnings:
    print(f"⚠️  Found {len(hvac_warnings)} HVAC-related warnings:")
    print("   - Air flow rates out of range")
    print("   - Coil frost/freeze warnings")
    print("   - Negative energy input ratios")
    print("   - These suggest HVAC system may not be properly configured")
else:
    print("✅ No major HVAC warnings")

print("\n6. SUMMARY OF ISSUES")
print("-" * 70)

issues = []
if 'lat_diff' in locals() and (lat_diff > 1 or lon_diff > 1):
    issues.append("❌ Location mismatch: IDF has wrong coordinates (not Chicago)")
if 'energy_diff' in locals() and energy_diff > 100:
    issues.append(f"❌ Energy mismatch: API reports {energy_diff_pct:.1f}% less than CSV")
if csv_area and abs(reported_area - csv_area) > 1:
    issues.append(f"❌ Area mismatch: API area differs from CSV by {abs(reported_area - csv_area):.2f} m²")
if geometry_warnings:
    issues.append(f"❌ Geometry issues: {len(geometry_warnings)} warnings about negative volumes")
if hvac_warnings:
    issues.append(f"⚠️  HVAC issues: {len(hvac_warnings)} warnings about system configuration")

if issues:
    print("FOUND ISSUES:")
    for issue in issues:
        print(f"  {issue}")
    print()
    print("RECOMMENDATIONS:")
    print("  1. Fix IDF location coordinates to match Chicago")
    print("  2. Investigate energy calculation discrepancy")
    print("  3. Fix geometry issues (negative volumes)")
    print("  4. Review HVAC system configuration")
else:
    print("✅ No major issues found")

print("\n" + "=" * 70)


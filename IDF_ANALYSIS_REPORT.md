# IDF Creator Service - Analysis Report

## Test Details
- **Address Used**: 987 W Chicago Ave, Chicago, IL 60622
- **Weather File**: test-chicago-weather.epw (Chicago O'Hare)
- **Building Type**: Office
- **Requested**: 500 m² floor area, 2 floors

---

## 🔴 CRITICAL ISSUES FOUND

### 1. Location Mismatch (CRITICAL)

**Problem**: The IDF file contains incorrect location coordinates that do NOT match Chicago.

- **IDF Location**: 44.9331°N, 7.5401°E (This is in Europe - near Turin, Italy!)
- **Expected Chicago Location**: 41.98°N, -87.92°W
- **Difference**: 2.95° latitude, 95.46° longitude

**Impact**: 
- EnergyPlus correctly used the weather file location instead (good!)
- But the IDF location data is fundamentally wrong
- This suggests the IDF creator service is not properly parsing the address or has hardcoded coordinates

**Fix Required**: The IDF creator service should:
1. Parse Chicago addresses and extract correct coordinates
2. Use geocoding to get accurate lat/lon for any address
3. Set correct time zone (-6.0 for Chicago, not -8.0)

---

### 2. Energy Calculation Discrepancy (CRITICAL)

**Problem**: The API reports much less energy than the actual simulation results.

**From CSV Data**:
- Total Site Energy: **939.83 GJ** = **261,000 kWh**
- Building Area: **421.67 m²**
- EUI: **2,228.82 MJ/m²** = **619 kWh/m²/year**

**From API Response**:
- Total Site Energy: **13,010.83 kWh** (only 5% of actual!)
- Building Area: **511.16 m²** (different area!)
- EUI: **25.45 kWh/m²/year** (only 4% of actual!)

**Analysis**:
- The API is reporting **95% less energy** than the simulation actually produced
- The building area is also different (511.16 vs 421.67 m²)
- This suggests the energy extraction/parsing logic has a bug

**Root Cause**: The energy parsing code is likely:
1. Reading from wrong meter or wrong units
2. Not converting GJ to kWh correctly
3. Using a different calculation method than the CSV report

---

### 3. Building Area Mismatch

**Problem**: Different building areas reported in different places.

- **CSV Report**: 421.67 m²
- **API Response**: 511.16 m²
- **Difference**: 89.49 m² (21% difference)

**Possible Causes**:
- API is using a different area calculation (e.g., including unconditioned spaces)
- CSV is using net conditioned area while API uses gross area
- Calculation error in the extraction code

---

## ⚠️ WARNINGS AND CONCERNS

### 4. Geometry Issues

The simulation had many warnings about:
- **Negative zone volumes** (all zones calculated as -ve, then defaulted to 10 m³)
- **Upside down floors/ceilings** (tilt angles incorrect)
- **Daylighting reference points outside zones**

**Impact**: These geometry issues can affect:
- Accurate volume calculations
- Proper heat transfer calculations
- Daylighting analysis

### 5. HVAC System Issues

The simulation had numerous HVAC warnings:
- **Air flow rates out of range** (occurred 65,000+ times)
- **Coil frost/freeze warnings** (outlet temps as low as -67°C)
- **Negative energy input ratios**
- **Low condenser temperatures**

**Impact**: The HVAC system appears to be improperly configured, which could affect:
- Energy consumption accuracy
- Comfort conditions
- System performance

### 6. EUI Value Concerns

**Reported EUI**: 25.45 kWh/m²/year

**Expected Range for Office Buildings**:
- Typical: 100-150 kWh/m²/year
- Low-performance: 50-100 kWh/m²/year
- High-performance: 150-300 kWh/m²/year

**Analysis**: 
- The reported EUI (25.45) is **extremely low** - suspiciously low for an office building
- The actual CSV EUI (619 kWh/m²/year) is **extremely high** - also suspicious
- This huge discrepancy suggests data extraction errors

---

## 📊 Energy Results Breakdown (from CSV)

From the actual EnergyPlus CSV output:

**Total Site Energy**: 939.83 GJ = 261,000 kWh

**Breakdown by End Use**:
- **Heating**: 139.10 GJ (electricity) + 689.22 GJ (natural gas) = 828.32 GJ
- **Cooling**: 13.29 GJ (electricity)
- **Interior Lighting**: 52.83 GJ (electricity)
- **Interior Equipment**: 28.01 GJ (electricity)
- **Fans**: 17.39 GJ (electricity)
- **Total Electricity**: 250.61 GJ = 69,600 kWh
- **Total Natural Gas**: 689.22 GJ = 191,400 kWh

**Peak Demand**: 16.1 kW (electricity) + 42.2 kW (gas heating)

**Comfort Issues**: 
- 3,718 hours where heating setpoint not met
- 3,195 hours where cooling setpoint not met
- 7,481 hours not comfortable (ASHRAE 55)

---

## ✅ What's Working

1. **Weather File Usage**: EnergyPlus correctly used the Chicago weather file location despite wrong IDF coordinates
2. **Simulation Completion**: The simulation ran successfully without fatal errors
3. **IDF Generation**: The service generated a valid, runnable IDF file
4. **File Structure**: The IDF has proper structure with zones, HVAC, schedules, etc.

---

## 🔧 Recommendations

### Immediate Fixes Required:

1. **Fix Location Parsing**
   - Implement proper geocoding for addresses
   - Extract correct lat/lon from address
   - Set correct time zone based on location

2. **Fix Energy Extraction**
   - Verify energy extraction from correct meters
   - Check unit conversions (GJ → kWh)
   - Compare extracted values with CSV reports
   - Fix the 95% energy under-reporting issue

3. **Fix Area Calculation**
   - Clarify which area is being reported (net vs gross)
   - Ensure consistency between CSV and API response

4. **Fix Geometry Issues**
   - Correct zone vertex ordering
   - Fix floor/ceiling tilt angles
   - Ensure all zones have positive volumes

5. **Review HVAC Configuration**
   - Check air flow rates
   - Verify coil sizing
   - Fix temperature setpoints

### Testing:

1. Verify energy extraction with known good IDF files
2. Compare API results with CSV outputs for validation
3. Test with multiple addresses to ensure location parsing works
4. Validate area calculations match EnergyPlus reporting

---

## Summary

The IDF creator service **generates valid IDF files** that can run simulations, but has **critical issues**:

1. ❌ **Location coordinates are wrong** (not parsing Chicago addresses correctly)
2. ❌ **Energy reporting is 95% too low** (extraction bug)
3. ❌ **Building area mismatch** (21% difference)
4. ⚠️ **Geometry warnings** (negative volumes, upside-down surfaces)
5. ⚠️ **HVAC configuration issues** (many warnings about flow rates, temperatures)

The **simulation itself runs correctly** and produces valid results, but the **data extraction and reporting** has serious bugs that need to be fixed.


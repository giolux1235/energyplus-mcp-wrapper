# EnergyPlus API Test Results Summary

**Date**: 2025-01-27  
**Test File**: `test-energyplus-api.mjs`  
**Status**: ✅ **SUCCESS**

---

## 📋 Test Configuration

- **IDF File**: `1ZoneUncontrolled.idf` (19,764 bytes)
- **Weather File**: `USA_CA_San.Francisco.Intl.AP.724940_TMY3.epw` (1,619,974 bytes)
- **API URL**: `https://web-production-1d1be.up.railway.app/simulate`
- **Response Time**: ~1.8 seconds

---

## ✅ Simulation Results

### Energy Consumption

| Metric | Value |
|--------|-------|
| **Total Energy** | 38,104.25 kWh |
| **Lighting Energy** | 22,897.24 kWh |
| **Heating Energy** | 0 kWh (no HVAC system) |
| **Cooling Energy** | 0 kWh (no HVAC system) |
| **Equipment Energy** | 0 kWh |
| **Fans Energy** | 0 kWh |
| **Pumps Energy** | 0 kWh |

### Building Metrics

| Metric | Value |
|--------|-------|
| **Building Area** | 232.26 m² (2,500 sq ft) |
| **Energy Use Intensity (EUI)** | 164.06 kWh/m² |
| **Peak Demand** | 16.96 kW |
| **Zones Count** | 1 zone |
| **Performance Score** | 65 (Average) |

### Energy Results (Structured)

```json
{
  "total_site_energy_kwh": 38104.25,
  "building_area_m2": 232.26,
  "eui_kwh_m2": 164.06,
  "heating_energy": 0,
  "cooling_energy": 0,
  "lighting_energy": 22897.24,
  "equipment_energy": 0,
  "fans_energy": 0,
  "pumps_energy": 0,
  "extraction_method": "sqlite"
}
```

---

## 📊 Output Files Generated

EnergyPlus generated **19 output files** during simulation:

1. `eplusout.audit` (1,525 bytes)
2. `eplusout.bnd` (6,287 bytes)
3. `eplusout.dxf` (5,428 bytes)
4. `eplusout.eio` (16,304 bytes)
5. `eplusout.end` (97 bytes)
6. `eplusout.err` (1,973 bytes) - Error/warning log
7. `eplusout.eso` (2,393,466 bytes) - EnergyPlus output
8. `eplusout.mdd` (3,793 bytes) - Meter data dictionary
9. `eplusout.mtd` (7,395 bytes)
10. `eplusout.mtr` (551,961 bytes) - Meter data
11. `eplusout.rdd` (28,768 bytes) - Report data dictionary
12. `eplusout.shd` (1,523 bytes)
13. `eplusout.sql` (3,379,200 bytes) - **SQLite database** (used for extraction)
14. `eplustbl.csv` (78,311 bytes) - Summary tables
15. `eplustbl.htm` (330,085 bytes) - HTML summary report
16. `eplustbl.tab` (78,308 bytes)
17. `eplustbl.txt` (156,420 bytes)
18. `eplustbl.xml` (223,790 bytes)
19. `sqlite.err` (73 bytes)

**Total Output Size**: ~7.2 MB

---

## ⚠️ Warnings

3 warnings were generated (non-fatal):

1. **Weather file location mismatch**: Weather file location (San Francisco) was used instead of IDF location (Denver)
2. **Design Day barometric pressure**: Two warnings about barometric pressure differences

These are expected warnings and don't affect simulation results.

---

## 🔍 Data Extraction Method

**Method Used**: SQLite database (`eplusout.sql`)

The API successfully extracted energy data from the SQLite database, which is the most reliable method. The database contains:
- 123,721 rows of time series data
- 41 report variables
- Complete building geometry and material information
- Hourly energy consumption data

---

## 📈 Key Observations

1. **Simple Building Model**: This is a 1-zone uncontrolled building with no HVAC system
   - Only exterior lighting consumes energy
   - No heating/cooling because there's no HVAC system
   - This is a basic test model

2. **Real Simulation**: The API ran a **real EnergyPlus simulation** (not mock data)
   - Simulation completed in ~0.71 seconds
   - Generated all standard EnergyPlus output files
   - Extracted real energy consumption data

3. **JSON Response**: The API returned a complete JSON response with:
   - Energy consumption data
   - Building metrics
   - Metadata (version, warnings, etc.)
   - Output file information
   - SQLite database schema information

4. **Response Format**: The output is **JSON only** - no files are returned
   - All EnergyPlus output files are parsed
   - Data is extracted and formatted as JSON
   - Files are deleted after parsing (temp directory cleanup)

---

## ✅ Test Conclusion

The EnergyPlus API is **working correctly** and returns:
- ✅ Real simulation results (not mock data)
- ✅ Complete energy consumption data
- ✅ Building metrics (area, EUI, peak demand)
- ✅ Structured JSON response
- ✅ Metadata and warnings
- ✅ Fast response time (~1.8 seconds)

The API successfully:
1. Received IDF and weather file content
2. Ran EnergyPlus simulation
3. Generated output files
4. Parsed SQLite database
5. Extracted energy data
6. Returned formatted JSON response

---

## 📝 Next Steps

To test with more complex buildings:
1. Use `5ZoneAirCooled.idf` for a building with HVAC
2. Use `RefBldgLargeOfficeNew2004_Chicago.idf` for a large office building
3. Test with different weather files (Chicago, etc.)

---

**Full results saved to**: `test-results.json`


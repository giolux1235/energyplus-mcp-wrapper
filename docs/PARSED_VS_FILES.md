# Parsed Data vs. Files: What You Need

## ✅ Short Answer

**For basic energy analysis: YES, the parsed data is sufficient. You don't need the files.**

**For detailed analysis: NO, you would need the files for:**
- Hourly time series data
- Monthly breakdowns
- Zone-by-zone analysis
- Detailed building geometry
- Full error logs

---

## 📊 What IS Parsed (Available in JSON)

### ✅ Energy Consumption Totals
- Total annual energy consumption (kWh)
- Electricity consumption (kWh)
- Natural gas consumption (kWh)
- Breakdown by end use:
  - Heating energy
  - Cooling energy
  - Lighting energy
  - Equipment energy
  - Fans energy
  - Pumps energy
  - Water systems energy
  - Heat rejection energy
  - etc.

### ✅ Building Metrics
- Building area (m²)
- Energy Use Intensity (EUI) - kWh/m²
- Peak demand (kW)
- Number of zones
- Performance score/rating

### ✅ Summary Information
- Warnings/errors (text summaries)
- Simulation metadata (version, timestamps)
- File names and sizes (metadata only)

---

## ❌ What is NOT Parsed (Only in Files)

### ❌ Time Series Data
The SQLite database contains **123,721 rows** of hourly time series data, but the API only extracts **annual totals**.

**What's in the files but NOT parsed:**
- Hourly energy consumption (8,760 hours × multiple variables)
- Hourly temperature data
- Hourly HVAC operation data
- Hourly zone temperatures
- Hourly occupancy data
- Hourly lighting schedules
- Hourly equipment loads

**Example from test results:**
```json
"ReportData": {
  "row_count": 123721,  // ← 123,721 hourly data points
  "columns": ["TimeIndex", "Value", ...]
}
```
**This data is NOT extracted** - only the final annual totals are.

### ❌ Monthly Breakdowns
- Monthly energy consumption
- Monthly peak demand
- Monthly EUI
- Seasonal analysis

### ❌ Zone-by-Zone Data
- Energy consumption per zone
- Temperature per zone
- Occupancy per zone
- HVAC loads per zone

### ❌ Detailed Building Information
- Full building geometry (surfaces, vertices)
- Material properties (detailed)
- Construction details
- HVAC system topology
- Schedule details

### ❌ Full Error/Warning Logs
- Complete error file content
- Detailed warning messages
- Simulation audit trail

---

## 🔍 Code Evidence

Looking at the extraction code, it **specifically skips hourly data**:

```python
# Line 1568-1569 in energyplus-robust-api.py
if freq and 'hourly' in freq.lower() and 'runperiod' not in freq.lower():
    logger.info(f"   Skipping hourly data: {name} ({freq})")
```

The API only extracts:
- **RunPeriod** totals (annual)
- **Facility-level** meters (not zone-level)
- **Summary** data (not time series)

---

## 📋 Comparison Table

| Data Type | Parsed in JSON? | Available in Files? | When You Need Files |
|-----------|----------------|---------------------|---------------------|
| **Annual Energy Totals** | ✅ Yes | ✅ Yes | ❌ No - JSON is enough |
| **Energy by End Use** | ✅ Yes | ✅ Yes | ❌ No - JSON is enough |
| **Building Area** | ✅ Yes | ✅ Yes | ❌ No - JSON is enough |
| **EUI** | ✅ Yes | ✅ Yes | ❌ No - JSON is enough |
| **Peak Demand** | ✅ Yes | ✅ Yes | ❌ No - JSON is enough |
| **Hourly Time Series** | ❌ No | ✅ Yes | ✅ **Yes - for charts/analysis** |
| **Monthly Breakdowns** | ❌ No | ✅ Yes | ✅ **Yes - for monthly reports** |
| **Zone-by-Zone Data** | ❌ No | ✅ Yes | ✅ **Yes - for zone analysis** |
| **Building Geometry** | ❌ No | ✅ Yes | ✅ **Yes - for visualization** |
| **Full Error Logs** | ❌ No | ✅ Yes | ✅ **Yes - for debugging** |

---

## 🎯 When You DON'T Need Files

**Use the parsed JSON data when you need:**
- ✅ Total annual energy consumption
- ✅ Energy breakdown by category
- ✅ Building performance metrics (EUI, peak demand)
- ✅ Summary reports
- ✅ Basic compliance checks
- ✅ Energy benchmarking
- ✅ Simple dashboards

**Example use cases:**
- "How much energy does this building use per year?"
- "What's the EUI?"
- "How much energy goes to heating vs cooling?"
- "What's the peak demand?"

---

## 🎯 When You DO Need Files

**You need the actual files when you need:**
- ❌ Hourly energy consumption charts
- ❌ Monthly energy breakdowns
- ❌ Time-of-day analysis
- ❌ Zone-by-zone comparisons
- ❌ Detailed building geometry visualization
- ❌ Full error logs for debugging
- ❌ Custom analysis beyond what's parsed

**Example use cases:**
- "Show me hourly energy consumption for January"
- "Compare energy use between zones"
- "Generate a detailed monthly report"
- "Visualize the building geometry"
- "Debug why the simulation failed"

---

## 💡 Solution: What to Do

### Option 1: Use Parsed Data (Current)
**Good for**: Basic energy analysis, dashboards, summaries

```javascript
// You get this in JSON:
{
  "total_energy_consumption": 38104.25,  // kWh/year
  "energy_intensity": 164.06,            // kWh/m²
  "heating_energy": 0,
  "cooling_energy": 0,
  "lighting_energy": 22897.24
}
```

### Option 2: Modify API to Extract More
**If you need hourly/monthly data**, you could modify the API to:
- Extract hourly time series from SQLite
- Extract monthly summaries
- Include zone-by-zone data
- Return larger JSON responses

**Trade-off**: Larger JSON responses (could be 10-50 MB instead of 5-50 KB)

### Option 3: Keep Files (Modify API)
**If you need full files**, modify the API to:
- Save files to persistent storage (S3, etc.)
- Return file URLs in JSON response
- Implement file retention policies

**Trade-off**: Storage costs, file management complexity

### Option 4: Run EnergyPlus Locally
**If you need full control**, run EnergyPlus locally:
```bash
energyplus -w weather.epw -d output_dir input.idf
# All files saved in output_dir/
```

---

## 📊 Real Example from Test

**What was parsed (in JSON):**
```json
{
  "total_energy_consumption": 38104.25,
  "lighting_energy": 22897.24,
  "building_area": 232.26,
  "energy_intensity": 164.06,
  "peak_demand": 16.96
}
```

**What was NOT parsed (but exists in files):**
- 123,721 hourly data points in SQLite
- 8,760 hours × 41 variables = 359,160 hourly values
- Monthly breakdowns
- Zone temperatures
- Detailed geometry
- Full error logs

---

## ✅ Conclusion

**For most webapp use cases: YES, the parsed data is sufficient.**

The API extracts all the **summary metrics** you need for:
- Energy dashboards
- Performance reports
- Compliance checks
- Basic analysis

**You only need the files if you need:**
- Detailed time series analysis
- Zone-by-zone comparisons
- Custom visualizations
- Advanced debugging

---

**Last Updated**: 2025-01-27


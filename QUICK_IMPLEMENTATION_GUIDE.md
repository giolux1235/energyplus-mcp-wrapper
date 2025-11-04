# Quick Implementation Guide - SQLite Extraction

## What the External API Needs to Do

1. **Add the `extract_energy_from_sqlite()` function** (see below)
2. **Call it when SQLite file exists** (after simulation completes)
3. **Return `energy_results` in the response** with the exact format
4. **Change `simulation_status` to "success"** when results are found

## Copy-Paste Ready Function

```python
import sqlite3
import os
import logging

logger = logging.getLogger(__name__)

def extract_energy_from_sqlite(sqlite_path):
    """Extract energy data from EnergyPlus SQLite database."""
    energy_data = {}
    
    try:
        if not os.path.exists(sqlite_path):
            return energy_data
        
        conn = sqlite3.connect(sqlite_path)
        cursor = conn.cursor()
        
        # Extract electricity
        electricity_kwh = 0
        try:
            cursor.execute("""
                SELECT SUM(rmd.Value) as TotalValue
                FROM ReportMeterData rmd
                JOIN ReportMeterDataDictionary rmdd 
                    ON rmd.ReportMeterDataDictionaryIndex = rmdd.ReportMeterDataDictionaryIndex
                WHERE rmdd.Name LIKE '%Electricity:Facility%'
                   OR rmdd.Name LIKE '%ElectricityNet:Facility%'
            """)
            result = cursor.fetchone()
            if result and result[0]:
                electricity_kwh = result[0] / 3600000  # J to kWh
        except:
            pass
        
        # Extract gas
        gas_kwh = 0
        try:
            cursor.execute("""
                SELECT SUM(rmd.Value) as TotalValue
                FROM ReportMeterData rmd
                JOIN ReportMeterDataDictionary rmdd 
                    ON rmd.ReportMeterDataDictionaryIndex = rmdd.ReportMeterDataDictionaryIndex
                WHERE rmdd.Name LIKE '%NaturalGas:Facility%'
                   OR rmdd.Name LIKE '%Gas:Facility%'
            """)
            result = cursor.fetchone()
            if result and result[0]:
                gas_kwh = result[0] / 3600000  # J to kWh
        except:
            pass
        
        # Extract building area
        building_area = 0
        try:
            cursor.execute("""
                SELECT AVG(rd.Value) as AvgValue
                FROM ReportData rd
                JOIN ReportDataDictionary rdd 
                    ON rd.ReportDataDictionaryIndex = rdd.ReportDataDictionaryIndex
                WHERE rdd.Name LIKE '%Total Building Area%'
                   OR rdd.Name LIKE '%Net Conditioned Building Area%'
                LIMIT 1
            """)
            result = cursor.fetchone()
            if result and result[0] and result[0] > 100:
                building_area = result[0]
        except:
            pass
        
        conn.close()
        
        # Calculate totals
        total_site_energy = electricity_kwh + gas_kwh
        
        if total_site_energy > 0:
            energy_data = {
                'total_energy_consumption': round(total_site_energy, 2),
                'electricity_kwh': round(electricity_kwh, 2),
                'gas_kwh': round(gas_kwh, 2),
                'building_area': round(building_area, 2)
            }
        
    except Exception as e:
        logger.error(f"SQLite extraction error: {e}")
    
    return energy_data
```

## Minimal Implementation Code

```python
# In your API handler after simulation:

# 1. Find SQLite file
output_dir = "/path/to/output"
sqlite_files = [f for f in os.listdir(output_dir) 
                if f.endswith(('.sqlite', '.sqlite3', '.db'))]

# 2. Extract energy data
energy_data = {}
if sqlite_files:
    sqlite_path = os.path.join(output_dir, sqlite_files[0])
    energy_data = extract_energy_from_sqlite(sqlite_path)

# 3. Build response
response = {
    "simulation_status": "success" if energy_data.get('total_energy_consumption', 0) > 0 else "error"
}

# 4. Add energy_results if extraction succeeded
if energy_data.get('total_energy_consumption', 0) > 0:
    total_site_energy = energy_data.get('total_energy_consumption', 0)
    building_area = energy_data.get('building_area', 0)
    eui = total_site_energy / building_area if building_area > 0 else 0
    
    response['energy_results'] = {
        "total_site_energy_kwh": round(total_site_energy, 2),
        "building_area_m2": round(building_area, 2),
        "eui_kwh_m2": round(eui, 2)
    }
```

## Key Points to Remember

### ⚠️ Critical: EnergyPlus Units

- **EnergyPlus stores values in Joules (J)**
- **Convert to kWh by dividing by 3,600,000**
- **Formula**: `kWh = Joules / 3,600,000`

### ✅ Multiple Query Strategies

- **Try multiple query strategies** - different EnergyPlus versions use different table schemas
- **If one strategy fails, try the next one**
- **Don't give up after first failure**

### ✅ Return Success When Results Found

- **Return "success" when results are extracted** - don't return "error" if SQLite extraction works
- **Even if CSV/HTML parsing failed, SQLite extraction can succeed**
- **Set `simulation_status = "success"` when `energy_results` is populated**

## Expected Response Format

```json
{
  "simulation_status": "success",
  "energy_results": {
    "total_site_energy_kwh": 12345.67,
    "building_area_m2": 4645.15,
    "eui_kwh_m2": 2.66
  }
}
```

### Field Definitions

- **`total_site_energy_kwh`**: Total site energy (electricity + gas) in kWh
- **`building_area_m2`**: Building floor area in square meters
- **`eui_kwh_m2`**: Energy Use Intensity (total_site_energy_kwh / building_area_m2)

## Integration Checklist

- [ ] Add `extract_energy_from_sqlite()` function
- [ ] Find SQLite file in output directory after simulation
- [ ] Call extraction function when SQLite file exists
- [ ] Calculate EUI (total_site_energy_kwh / building_area_m2)
- [ ] Build `energy_results` object with exact field names
- [ ] Set `simulation_status = "success"` when extraction succeeds
- [ ] Handle errors gracefully (don't crash if SQLite extraction fails)
- [ ] Test with real EnergyPlus SQLite files

## Common Issues

### Issue: No energy data extracted

**Solution**: Try multiple query strategies (see full specification document)

### Issue: Wrong units (values too large)

**Solution**: Remember to divide by 3,600,000 to convert Joules to kWh

### Issue: Building area is 0

**Solution**: Try different area extraction queries (see full specification)

### Issue: Gas is 0 for all-electric building

**Solution**: This is normal - not all buildings have gas meters

## Quick Reference: SQL Query Patterns

### Electricity
```sql
WHERE rmdd.Name LIKE '%Electricity:Facility%'
```

### Gas
```sql
WHERE rmdd.Name LIKE '%NaturalGas:Facility%'
```

### Building Area
```sql
WHERE rdd.Name LIKE '%Total Building Area%'
```

## Testing

1. Run EnergyPlus simulation with SQLite output enabled
2. Check output directory for `.sqlite` or `.sqlite3` file
3. Call extraction function
4. Verify `energy_results` contains valid data
5. Check that `total_site_energy_kwh` = `electricity_kwh` + `gas_kwh`
6. Verify EUI calculation is correct

## Next Steps

- See `EXTERNAL_API_SQLITE_EXTRACTION_SPEC.md` for complete specification
- Implement all 5 electricity strategies for maximum compatibility
- Implement all 3 gas strategies
- Implement all 3 building area strategies
- Add comprehensive error handling
- Add logging for debugging


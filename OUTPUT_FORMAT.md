# Output Format Documentation

## 📤 Output Type: **JSON Response** (Not Files)

The EnergyPlus API returns **JSON data**, not files. However, EnergyPlus generates files during simulation, which are then parsed and converted to JSON.

---

## 🔄 Output Flow

```
1. EnergyPlus Simulation
   ↓
   Generates files in temp directory:
   - eplusout.sql (SQLite database)
   - eplusout.html (HTML summary)
   - eplusout.csv (CSV data)
   - eplusout.err (errors/warnings)
   ↓
2. API Parses Files
   ↓
3. Files Deleted (temp directory cleanup)
   ↓
4. JSON Response Returned
```

---

## 📋 JSON Response Structure

### Success Response

```json
{
  "version": "33.0.0",
  "simulation_status": "success",
  "energyplus_version": "25.1.0",
  "real_simulation": true,
  "exit_code": 0,
  "warnings_count": 5,
  "warnings": [
    "** Warning ** Some warning message"
  ],
  "processing_time": "2025-01-27T10:30:45.123456",
  
  // Energy Consumption Data
  "total_energy_consumption": 125000.50,  // kWh
  "electricity_kwh": 100000.25,
  "gas_kwh": 25000.25,
  "heating_energy": 45000.00,  // kWh
  "cooling_energy": 35000.00,  // kWh
  "lighting_energy": 25000.00,  // kWh
  "equipment_energy": 20000.00,  // kWh
  "fans_energy": 5000.00,  // kWh
  "pumps_energy": 3000.00,  // kWh
  
  // Building Metrics
  "building_area": 1000.00,  // m²
  "energy_intensity": 125.00,  // kWh/m² (EUI)
  "zones_count": 5,
  "peak_demand": 450.5,  // kW
  
  // Energy Results (structured format)
  "energy_results": {
    "total_site_energy_kwh": 125000.50,
    "building_area_m2": 1000.00,
    "eui_kwh_m2": 125.00,
    "heating_energy": 45000.00,
    "cooling_energy": 35000.00,
    "lighting_energy": 25000.00,
    "equipment_energy": 20000.00,
    "fans_energy": 5000.00,
    "pumps_energy": 3000.00,
    "extraction_method": "sqlite"  // or "html", "csv", "mtr"
  },
  
  // Additional Analysis (if available)
  "building_analysis": {
    "building_type": "Office",
    "hvac_systems": [...],
    "materials": [...]
  },
  "weather_analysis": {
    "location": "Chicago, IL",
    "climate_zone": "5A",
    "hdd": 4500,
    "cdd": 1200
  },
  "hvac_analysis": {
    "systems": [...],
    "efficiency": {...}
  },
  "recommendations": [
    {
      "type": "energy_savings",
      "description": "Upgrade lighting to LED",
      "potential_savings": 5000  // kWh/year
    }
  ],
  
  // Output File Metadata (for debugging)
  "output_files": [
    "eplusout.sql",
    "eplusout.html",
    "eplusout.csv",
    "eplusout.err"
  ],
  "sqlite_file": "eplusout.sql",
  "sqlite_size_bytes": 524288
}
```

### Error Response

```json
{
  "version": "33.0.0",
  "simulation_status": "error",
  "energyplus_version": "25.1.0",
  "real_simulation": true,
  "error_message": "EnergyPlus simulation failed: Fatal error in IDF file",
  "processing_time": "2025-01-27T10:30:45.123456",
  "warnings": [
    "** Warning ** Some warning message"
  ]
}
```

---

## 📊 Data Extraction Methods

The API tries multiple methods to extract energy data (in order of preference):

1. **SQLite Database** (`eplusout.sql`) - Most reliable
   - Contains structured meter data
   - Fast querying
   - Complete data

2. **HTML Summary** (`eplusout.html`) - Second choice
   - Contains formatted tables
   - End Uses table
   - Building area

3. **CSV Files** (`eplusout.csv`, `eplusoutMeter.csv`) - Fallback
   - Time series data
   - Meter readings

4. **MTR Files** (`eplusout.mtr`) - Last resort
   - Meter data in text format

The `extraction_method` field in the response indicates which method was used.

---

## 🔍 Key Fields Explained

### Energy Consumption
- `total_energy_consumption`: Total energy in kWh (electricity + gas)
- `electricity_kwh`: Electricity consumption in kWh
- `gas_kwh`: Natural gas consumption in kWh
- `heating_energy`: Energy used for heating (kWh)
- `cooling_energy`: Energy used for cooling (kWh)
- `lighting_energy`: Energy used for lighting (kWh)
- `equipment_energy`: Energy used for equipment/plug loads (kWh)

### Building Metrics
- `building_area`: Total floor area in square meters (m²)
- `energy_intensity`: Energy Use Intensity (EUI) in kWh/m²
- `zones_count`: Number of thermal zones
- `peak_demand`: Peak electrical demand in kW

### Status Fields
- `simulation_status`: `"success"` or `"error"`
- `real_simulation`: Always `true` (no mock data)
- `exit_code`: EnergyPlus exit code (0 = success)
- `warnings_count`: Number of warnings
- `warnings`: Array of warning messages

---

## 📥 How to Use the Output

### In JavaScript/TypeScript

```typescript
const response = await fetch('https://api-url/simulate', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    idf_content: idfContent,
    weather_content: weatherContent
  })
});

const data = await response.json();

if (data.simulation_status === 'success') {
  console.log(`Total Energy: ${data.total_energy_consumption} kWh`);
  console.log(`EUI: ${data.energy_intensity} kWh/m²`);
  console.log(`Building Area: ${data.building_area} m²`);
  
  // Access structured results
  const energyResults = data.energy_results;
  console.log(`Heating: ${energyResults.heating_energy} kWh`);
  console.log(`Cooling: ${energyResults.cooling_energy} kWh`);
} else {
  console.error(`Error: ${data.error_message}`);
}
```

### In Python

```python
import requests
import json

response = requests.post('https://api-url/simulate', json={
    'idf_content': idf_content,
    'weather_content': weather_content
})

data = response.json()

if data['simulation_status'] == 'success':
    print(f"Total Energy: {data['total_energy_consumption']} kWh")
    print(f"EUI: {data['energy_intensity']} kWh/m²")
    print(f"Building Area: {data['building_area']} m²")
else:
    print(f"Error: {data['error_message']}")
```

---

## 📁 What About the Actual Files?

### Files Are Available for Download

The EnergyPlus output files (`.sql`, `.html`, `.csv`, `.err`, etc.) are:
- ✅ Generated during simulation
- ✅ Parsed by the API (data included in JSON response)
- ✅ **Saved and available for download** via download URLs
- ✅ **Available for 24 hours** (configurable via `FILE_RETENTION_HOURS`)

### Downloading Output Files

The API response includes `output_files_download` with download URLs:

```json
{
  "simulation_status": "success",
  "simulation_id": "550e8400-e29b-41d4-a716-446655440000",
  "output_files_download": {
    "eplusout.sql": {
      "url": "/download/550e8400-e29b-41d4-a716-446655440000/eplusout.sql",
      "size_bytes": 3379200,
      "size_mb": 3.22
    },
    "eplustbl.htm": {
      "url": "/download/550e8400-e29b-41d4-a716-446655440000/eplustbl.htm",
      "size_bytes": 330085,
      "size_mb": 0.31
    }
    // ... all 19 output files
  },
  "download_base_url": "https://web-production-1d1be.up.railway.app",
  "files_available_until": "2025-11-07T08:18:13.485598"
}
```

**Download Example:**
```javascript
// Construct full download URL
const fileUrl = `${data.download_base_url}${data.output_files_download['eplusout.sql'].url}`;
// Download the file
window.open(fileUrl, '_blank');
```

See [FILE_DOWNLOAD_FEATURE.md](./FILE_DOWNLOAD_FEATURE.md) for complete details on downloading files.

---

## 🔄 Response Format from Supabase Edge Function

The Supabase edge function (`run-simulation`) transforms the API response:

```typescript
// Original API response
{
  "total_energy_consumption": 125000,
  "energy_intensity": 125,
  ...
}

// Transformed by edge function
{
  "success": true,
  "summary": {
    "totalEnergyUse": "125,000 kWh",  // Formatted string
    "energyUseIntensity": "125 kWh/m²",
    "buildingArea": "1,000 m²",
    ...
  },
  "apiMetadata": {
    "version": "33.0.0",
    "simulationStatus": "success",
    ...
  }
}
```

The edge function:
- Formats numbers with commas
- Adds units to strings
- Wraps in `summary` object
- Adds metadata in `apiMetadata`

---

## 📊 Example Complete Response

```json
{
  "version": "33.0.0",
  "simulation_status": "success",
  "energyplus_version": "25.1.0",
  "real_simulation": true,
  "exit_code": 0,
  "warnings_count": 3,
  "warnings": [
    "** Warning ** Zone 'ZONE1' has no surfaces",
    "** Warning ** Material 'MAT1' has unusual properties"
  ],
  "processing_time": "2025-01-27T10:30:45.123456",
  "total_energy_consumption": 125000.50,
  "electricity_kwh": 100000.25,
  "gas_kwh": 25000.25,
  "heating_energy": 45000.00,
  "cooling_energy": 35000.00,
  "lighting_energy": 25000.00,
  "equipment_energy": 20000.00,
  "fans_energy": 5000.00,
  "pumps_energy": 3000.00,
  "building_area": 1000.00,
  "energy_intensity": 125.00,
  "zones_count": 5,
  "peak_demand": 450.5,
  "energy_results": {
    "total_site_energy_kwh": 125000.50,
    "building_area_m2": 1000.00,
    "eui_kwh_m2": 125.00,
    "heating_energy": 45000.00,
    "cooling_energy": 35000.00,
    "lighting_energy": 25000.00,
    "equipment_energy": 20000.00,
    "fans_energy": 5000.00,
    "pumps_energy": 3000.00,
    "extraction_method": "sqlite"
  },
  "output_files": [
    "eplusout.sql",
    "eplusout.html",
    "eplusout.csv",
    "eplusout.err"
  ],
  "sqlite_file": "eplusout.sql",
  "sqlite_size_bytes": 524288
}
```

---

## ✅ Summary

- **Output Type**: JSON (not files)
- **Format**: HTTP JSON response
- **Content**: Parsed energy data, building metrics, warnings
- **Files**: Generated but not returned (parsed and deleted)
- **Size**: Typically 5-50 KB (depends on data complexity)

---

**Last Updated**: 2025-01-27


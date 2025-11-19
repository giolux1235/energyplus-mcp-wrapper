# Local Energy Extraction Tool

## Overview

The `extract-energy-local.py` script allows you to extract energy consumption data from EnergyPlus output files locally, without needing to run the full API service.

## Usage

### Extract from Output Directory

```bash
python extract-energy-local.py <output_directory> --period-days 7
```

Example:
```bash
python extract-energy-local.py EnergyPlus-MCP/energyplus-mcp-server/outputs --period-days 7
```

### Extract from SQLite File

```bash
python extract-energy-local.py eplusout.sql --period-days 7
```

### Save to File

```bash
python extract-energy-local.py <output_directory> --period-days 7 --output results.json
```

### Options

- `--period-days`: Simulation period in days (default: 7 for 1-week simulations)
- `--output, -o`: Save results to JSON file (default: print to stdout)
- `--verbose, -v`: Enable verbose logging

## Output Format

```json
{
  "simulation_period_days": 7,
  "energy_data": {
    "total_energy_consumption": 18132.7,
    "heating_energy": 0,
    "cooling_energy": 0,
    "lighting_energy": 0,
    "equipment_energy": 0,
    "building_area": 4999.99,
    "electricity_kwh": 18132.7,
    "gas_kwh": 0
  },
  "extraction_method": "local"
}
```

## Benefits

1. **Fast Testing**: Test extraction logic without deploying to Railway
2. **Debugging**: Easier to debug extraction issues locally
3. **Offline**: Works with downloaded EnergyPlus output files
4. **Flexible**: Can extract from single files or directories

## Integration with API

The API supports skipping extraction via environment variable:

### Option 1: API with Extraction (Default)
```bash
# API extracts energy automatically
curl -X POST https://web-production-1d1be.up.railway.app/simulate \
  -H "Content-Type: application/json" \
  -d '{"idf_content": "...", "weather_content": "..."}'
# Returns: {"simulation_status": "success", "total_energy_consumption": 18132.7, ...}
```

### Option 2: API without Extraction (Local Extraction)
Set `SKIP_ENERGY_EXTRACTION=true` in Railway environment variables, then:

```bash
# API returns raw output files info (no extraction)
curl -X POST https://web-production-1d1be.up.railway.app/simulate \
  -H "Content-Type: application/json" \
  -d '{"idf_content": "...", "weather_content": "..."}'
# Returns: {"simulation_status": "success", "output_files": [...], "extraction_skipped": true}

# Download output files, then extract locally:
python extract-energy-local.py downloaded_outputs/ --period-days 7
```

## Example Workflow

1. Run simulation via API (or locally)
2. Download output files (SQLite, CSV, HTML)
3. Extract energy data locally:
   ```bash
   python extract-energy-local.py outputs/ --period-days 7 --output results.json
   ```
4. Use results for analysis/reporting


# Repository Organization

This document describes the organization of the repository after cleanup.

## Directory Structure

```
energyplus test/
├── tests/                    # All test files organized by category
│   ├── api/                  # API endpoint tests
│   ├── simulation/           # Simulation functionality tests
│   ├── analysis/             # Analysis and extraction scripts
│   ├── comprehensive/        # Comprehensive test suites
│   ├── weather/             # Weather file handling tests
│   └── scripts/             # Utility test scripts
│
├── docs/                     # Documentation files
│   ├── WEATHER_FILE_HANDLING_REPORT.md
│   ├── ENERGY_ANNUALIZATION_FIX.md
│   └── ... (other docs)
│
├── logs/                     # Log files and test outputs
│
├── ashrae901_examples/       # ASHRAE 901 example IDF files
├── ashrae901_weather/        # Weather files for ASHRAE 901
├── ashrae901_test_outputs/   # ASHRAE 901 test outputs
├── nrel_testfiles/           # NREL test IDF files
├── test_outputs/             # General test outputs
├── test_iterations_local/    # Iteration tracking data
│
├── EnergyPlus-MCP/           # EnergyPlus MCP server code
├── speed-build-engine/       # Speed build engine project
│
├── energyplus-robust-api.py  # Main API server
├── extract-energy-local.py   # Energy extraction script
├── requirements.txt          # Python dependencies
├── package.json             # Node.js dependencies
└── README.md                # Main README
```

## Test Files Organization

### `/tests/api/` - API Tests
- `test-energyplus-api.mjs` - Basic API connectivity
- `test-energy-consistency.mjs` - Energy value consistency
- `test-idf-and-simulation.js/mjs` - IDF generation workflow

### `/tests/simulation/` - Simulation Tests
- `test-simple-idf-simulation.mjs` - Simple simulation
- `test-multiple-idfs.mjs` - Multiple IDF testing
- `test-simulation-period-limits.mjs` - Period limit tests
- `test-actual-period-limits.mjs` - Actual period tests
- `test-local-simulation-from-idf-creator.mjs` - Local simulation

### `/tests/analysis/` - Analysis Scripts
- `analyze-api-response.mjs` - API response analysis
- `analyze-energy-results.mjs` - Energy results analysis
- `analyze-full-results.mjs` - Comprehensive analysis
- `analyze-warnings.mjs` - Warning analysis
- `test-local-extraction.mjs` - Local extraction tests
- `extract-and-analyze.mjs` - Extract and analyze

### `/tests/comprehensive/` - Comprehensive Test Suites
- `comprehensive-idf-test.mjs` - Main comprehensive test
- `comprehensive-idf-test-iterative.mjs` - Iterative testing
- `comprehensive-real-simulation-test.js/mjs` - Real simulation suite
- `quick-api-test.mjs` - Quick API tests
- `run-multiple-tests.mjs` - Multiple test runner
- `test-ashrae901-examples.mjs` - ASHRAE 901 tests

### `/tests/weather/` - Weather File Tests
- `test-weather-file-handling.mjs` - Weather file handling
- `test-weather-matching.mjs` - Weather matching logic
- `test-annualization.mjs` - Energy annualization tests

## Running Tests

All test files maintain their original functionality. Path references use `process.cwd()` or relative paths, so they work from any directory.

### Examples:
```bash
# Run from root
node tests/api/test-energyplus-api.mjs

# Run from tests directory
cd tests/api
node test-energyplus-api.mjs

# Run comprehensive suite
node tests/comprehensive/comprehensive-idf-test.mjs
```

## Documentation

All documentation files have been moved to `/docs/` for better organization.

## Logs

All log files (*.txt, *.log) have been moved to `/logs/` directory.


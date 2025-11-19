# Tests Directory

This directory contains all test scripts organized by category.

## Directory Structure

### `/api/` - API Tests
Tests for the EnergyPlus API endpoint functionality:
- `test-energyplus-api.mjs` - Basic API connectivity and response tests
- `test-energy-consistency.mjs` - Tests energy value consistency across runs
- `test-idf-and-simulation.js/mjs` - Tests IDF generation and simulation workflow

### `/simulation/` - Simulation Tests
Tests for EnergyPlus simulation functionality:
- `test-simple-idf-simulation.mjs` - Simple simulation test
- `test-multiple-idfs.mjs` - Tests multiple IDF files
- `test-local-simulation-from-idf-creator.mjs` - Local simulation tests
- `test-simulation-period-limits.mjs` - Tests simulation period limits
- `test-simulation-limits-no-optimization.mjs` - Tests without optimization
- `test-actual-period-limits.mjs` - Tests actual period limits

### `/analysis/` - Analysis Scripts
Scripts for analyzing simulation results:
- `analyze-api-response.mjs` - Analyzes API response structure
- `analyze-energy-results.mjs` - Analyzes energy simulation results
- `analyze-full-results.mjs` - Comprehensive results analysis
- `analyze-warnings.mjs` - Analyzes EnergyPlus warnings
- `test-local-extraction.mjs` - Tests local energy extraction
- `extract-and-analyze.mjs` - Extract and analyze energy data

### `/comprehensive/` - Comprehensive Test Suites
Full test suites for comprehensive testing:
- `comprehensive-idf-test.mjs` - Comprehensive IDF file testing
- `comprehensive-idf-test-iterative.mjs` - Iterative IDF testing with progress tracking
- `comprehensive-real-simulation-test.js/mjs` - Real simulation test suite
- `quick-api-test.mjs` - Quick API test suite
- `run-multiple-tests.mjs` - Run multiple tests in sequence
- `test-ashrae901-examples.mjs` - Tests ASHRAE 901 example files

### `/weather/` - Weather File Tests
Tests for weather file handling:
- `test-weather-file-handling.mjs` - Tests weather file handling in API
- `test-weather-matching.mjs` - Tests weather file matching logic
- `test-annualization.mjs` - Tests energy annualization fix

## Running Tests

### Run all API tests:
```bash
cd tests/api
node test-energyplus-api.mjs
```

### Run comprehensive test suite:
```bash
cd tests/comprehensive
node comprehensive-idf-test.mjs
```

### Run weather file tests:
```bash
cd tests/weather
node test-weather-file-handling.mjs
```

## Test Data

Test data files are located in:
- `../ashrae901_examples/` - ASHRAE 901 example IDF files
- `../ashrae901_weather/` - Weather files for ASHRAE 901 tests
- `../EnergyPlus-MCP/energyplus-mcp-server/sample_files/` - Sample IDF and weather files
- `../nrel_testfiles/` - NREL test IDF files

## Test Outputs

Test outputs are saved to:
- `../test_outputs/` - General test outputs
- `../ashrae901_test_outputs/` - ASHRAE 901 test outputs
- `../test_iterations_local/` - Iteration tracking data

## Notes

- Most tests require the EnergyPlus API to be running at `https://web-production-1d1be.up.railway.app/simulate`
- Some tests require local IDF and weather files
- Test progress is tracked in `../test_progress_local.json`

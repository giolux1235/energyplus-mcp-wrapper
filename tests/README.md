# Tests Directory

This directory contains all test documentation, scripts, and related materials for the EnergyPlus project.

## Structure

```
tests/
├── docs/           # Test documentation and reports
├── scripts/        # Test scripts and utilities
└── samples/        # Sample test data and files
```

## Test Documentation

- `docs/REAL_DATA_TEST_SUMMARY.md` - Real data test summary using NREL building data

## Test Scripts

- `scripts/auto-run-simulation.js` - Automated simulation runner
- `scripts/check-simulation-results.js` - Simulation results checker
- `scripts/run-complete-simulation.js` - Complete simulation runner
- `scripts/run-real-simulation.js` - Real-world simulation runner
- `scripts/test-address-to-idf.js` - Address to IDF conversion tester
- `scripts/test-idf-parser.js` - IDF parser test script

## Unit Tests

Unit tests for the EnergyPlus-MCP server module are located in:
- `EnergyPlus-MCP/energyplus-mcp-server/tests/`

## Notes

- Test output files (logs, results, etc.) are excluded via `.gitignore`
- Test scripts may require specific environment setup - see individual script documentation
- Sample test files are available in `nrel_testfiles/` and `sample_files/` directories


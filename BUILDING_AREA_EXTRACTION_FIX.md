# Building Area Extraction Fix

## Problem
The EnergyPlus API was using a hardcoded fallback value of **511.16 m²** when building area extraction failed, causing incorrect EUI calculations.

## Root Cause
1. HTML parsing regex patterns might not match all HTML formats
2. SQLite extraction might fail silently
3. CSV parsing was not extracting building area
4. Fallback was used without warnings

## Fixes Applied

### 1. Enhanced CSV Parsing (`parse_energyplus_csv`)
- **Added building area extraction from CSV files**
- Parses both inline format: `,Total Building Area,421.67,`
- And header + value format: `,,Area [m2],` followed by value line
- Validates area is in reasonable range (50-50000 m²)

### 2. Improved Extraction Strategy (`parse_all_output_files`)
- **CSV parsing now runs for ALL CSV files** (not just as fallback for energy)
- **Building area from CSV always takes priority** if found
- CSV is considered the most reliable source for building area

### 3. Better Error Handling (`add_calculated_metrics`)
- **Added warning logs** when fallback value is used
- **Flags extraction failure** with `_area_extraction_failed` flag
- **Validates extracted area** is in reasonable range
- Makes it obvious when default value is being used

## Code Changes

### File: `energyplus-robust-api.py`

1. **Lines 510-595**: Enhanced `parse_energyplus_csv()` to extract building area
2. **Lines 336-350**: Updated CSV parsing strategy to always run and prioritize area
3. **Lines 1162-1180**: Added warnings and validation in `add_calculated_metrics()`

## Expected Behavior After Fix

1. **Primary**: Building area extracted from CSV (most reliable)
2. **Secondary**: Building area from HTML table
3. **Tertiary**: Building area from SQLite database
4. **Last Resort**: Hardcoded 511.16 m² with **clear warnings**

## Testing

To verify the fix works:
1. Run a simulation that produces CSV output
2. Check logs for: `✅ Building area from CSV: X.XX m²`
3. Verify the reported area matches the CSV value (not 511.16)
4. If fallback is used, warnings should appear in logs

## Impact

- ✅ Building area will now be extracted correctly from CSV
- ✅ EUI calculations will be accurate
- ✅ Clear warnings when extraction fails
- ✅ No silent failures

---

**Status**: ✅ Fixed - Building area extraction now includes CSV parsing as primary method


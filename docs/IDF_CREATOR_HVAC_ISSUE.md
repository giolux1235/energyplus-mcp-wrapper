# Critical HVAC Node Connection Issue in IDF Creator

## Problem Summary
The IDF Creator service is generating IDF files with **HVAC node connection errors** that prevent EnergyPlus simulations from running.

## Error Details
EnergyPlus reports **29 Severe Errors** all related to missing HVAC nodes:
```
** Severe  ** GetAirPathData: AirLoopHVAC="LOBBY_0_Z1_AIRLOOP", branch in error.
**   ~~~   ** Probable missing or misspelled node referenced in the branch(es):
**   ~~~   ** Possible Error in Branch Object="LOBBY_0_Z1_MAINBRANCH".
**   ~~~   ** ...looking to match to Node="LOBBY_0_Z1_SUPPLYEQUIPMENTOUTLETNODE".
```

This error repeats for all 29 zones in the building.

## Root Cause - CONFIRMED
The IDF files have **case sensitivity mismatch** in node names:
- **Node exists as**: `lobby_0_z1_SupplyEquipmentOutletNode` (lowercase, mixed case)
- **EnergyPlus/Branch expects**: `LOBBY_0_Z1_SUPPLYEQUIPMENTOUTLETNODE` (all uppercase)
- **EnergyPlus is case-sensitive** for node names
- The node appears 3 times in the IDF (correctly defined) but Branch objects reference it with wrong case

**Evidence**:
- ✅ Node `lobby_0_z1_SupplyEquipmentOutletNode` exists in IDF (appears 3 times)
- ❌ Node `LOBBY_0_Z1_SUPPLYEQUIPMENTOUTLETNODE` does NOT exist in IDF
- Branch objects are referencing the uppercase version that doesn't exist

## Impact
- **All simulations fail** before they can start
- **No energy results** can be generated
- This is a **blocking issue** - prevents any testing of the IDF Creator service

## Additional Issues Found

### 1. Version Mismatch Warning
```
** Warning ** Version: in IDF="25.1" not the same as expected="24.2"
```
- IDF files are generated for EnergyPlus 25.1
- Local EnergyPlus installation is version 24.2.0
- This may cause compatibility issues

### 2. Zone Area Warning
```
** Warning ** GetSurfaceData: Entered Zone Floor Area(s) differ more than 5% from the sum of the Space Floor Area(s).
```
- Zone floor areas don't match space floor areas
- May indicate geometry calculation issues

## Comparison with Previous Tests

### Previous Successful Tests (Earlier Today)
- Simulations **completed successfully**
- Energy values were extracted (though unrealistically low)
- No HVAC node errors reported

### Current Tests (Now)
- All simulations **fail immediately**
- HVAC node connection errors prevent execution
- **Cannot extract any energy data**

## Possible Causes

1. **IDF Creator Service Updated**: The service may have been updated and now generates different HVAC configurations
2. **Node Naming Convention Changed**: The naming convention for nodes may have changed (case sensitivity)
3. **Missing Node Definitions**: The HVAC equipment may not be creating the required outlet nodes
4. **Branch Configuration Error**: The Branch objects may be referencing nodes that don't exist

## Required Fixes

### Immediate (Critical)
1. **Fix Node Naming Consistency**:
   - Ensure all node names use consistent case (preferably all uppercase or all lowercase)
   - Verify that referenced nodes actually exist in the IDF
   - Check that AirLoopHVAC, Branch, and Equipment objects all use the same node names

2. **Verify HVAC Equipment Creates Required Nodes**:
   - Ensure all HVAC equipment (fans, coils, etc.) create outlet nodes
   - Verify that these nodes are properly named and referenced

3. **Test with EnergyPlus 24.2**:
   - Either downgrade IDF version to 24.2 or test compatibility
   - Or document that IDF Creator requires EnergyPlus 25.1+

### Recommended
1. **Add Node Validation**:
   - Before generating IDF, validate that all referenced nodes exist
   - Check for case sensitivity issues
   - Verify node connections are complete

2. **Add Simulation Test**:
   - Run a quick EnergyPlus validation on generated IDF files
   - Return errors to the user if IDF is invalid
   - Or provide a `/validate` endpoint

## Test Results

### Test Attempts
- **5 different addresses tested**
- **All 5 failed** with the same HVAC node errors
- **0 successful simulations**

### Error Pattern
- Same error pattern for all zones
- All AirLoopHVAC systems affected
- Error occurs during input processing (before simulation starts)

## Next Steps

1. **Report to IDF Creator Team**: This is a blocking issue that needs immediate attention
2. **Check Service Logs**: Review IDF Creator service logs to see if there were recent changes
3. **Test with EnergyPlus 25.1**: If available, test if the issue is version-specific
4. **Workaround**: Consider disabling HVAC systems for testing, or using simpler HVAC configurations

## Status
🔴 **CRITICAL BLOCKER** - IDF Creator service is currently generating invalid IDF files that cannot be simulated.


# IDF Creator Outstanding Issues (EnergyPlus 24.2.0)

**Date:** 7 Nov 2025  
**Prepared by:** EnergyPlus local QA  
**Scope:** Errors/warnings that still originate in the IDF files returned by `https://web-production-3092c.up.railway.app`. Local tooling has been fixed; these are service-side items only.

---

## Summary Table

| Priority | Issue | Evidence | Impact | Recommended Action |
| --- | --- | --- | --- | --- |
| Critical | Ideal loads system missing return node/plenum hookup | Fatal: `InitPurchasedAir: ... cannot find ZoneHVAC:ReturnPlenum` | Simulation halts before HVAC sizing | Provide matching exhaust/return nodes or remove unused plenum references |
| Critical | Zone equipment nodes duplicated | Fatal: `ZoneHVAC:EquipmentConnections ... duplicate node name="BUILDING_ZONE_1 SUPPLY NODE"` | EnergyPlus aborts before sizing | Give each inlet/zone/return node unique names; update equipment lists accordingly |
| Critical | Subsurfaces emitted on the wrong face orientation | Fatal: `checkSubSurfAzTiltNorm ... differs more than 90° from base surface` | Simulation halts in `GetSurfaceData` before sizing | Align window vertices to match parent wall orientation (respect `GlobalGeometryRules`) |
| Critical | `Site:Location` names contain commas and break field parsing | Fatal: `Line ... Error parsing "Site:Location"... "200.0" is not a valid Object Type.` | EnergyPlus aborts before reading geometry or sizing | Remove commas (or wrap in quotes) in name fields when emitting IDF objects |
| Critical | Multiple `OutdoorAir:Node` objects share the same name | Fatal: `OutdoorAir:Node, duplicate Name = SITE OUTDOOR AIR NODE` | Simulation halts before sizing | Ensure each OA node name is unique or use a NodeList/connector to share |
| Critical | DX coils sized inconsistently, yielding saturated outlet air | Warmup warnings: coil RH > 100 % for every DX coil | Coil sizing invalid, cascades into frost/psych failures | Autosize capacity/airflow/SHR together within EnergyPlus limits |
| Critical | Coil frost / outlet air < −80 °C | 24 000–27 000 warnings per coil (previous runs) | Invalid psychrometrics, zero sensible loads | Fix coil sizing (above) + add minimum outlet/operation limits |
| High | Low condenser dry-bulb temperatures (<0 °C) | 100–150 warnings per coil | Model outside spec; requires defrost logic | Add min outdoor temp cutoff or heat-pump model |
| High | Psychrometric failures (`PsyWFnTdbH` invalid) | ~230 000 warnings | Energy results meaningless | Resolved once coils operate in valid regime |
| Medium | EUI ≈ 0.52 kWh/m²·yr | All test cases | Indicates loads are not delivered | After sizing fix, review schedules & heating provision |

Each item is documented in detail below with suggested fixes and references.

## 0. Ideal Loads System Missing Return Node (Critical)

### EnergyPlus Output
```
** Severe ** InitPurchasedAir: ZoneHVAC:IdealLoadsAirSystem = BUILDING_ZONE_1_HVAC cannot find ZoneHVAC:ReturnPlenum.
**  Fatal  ** InitPurchasedAir: In ZoneHVAC:IdealLoadsAirSystem = BUILDING_ZONE_1_HVAC
```

### Root Cause
- The generated `ZoneHVAC:IdealLoadsAirSystem` references a return plenum node that is never defined, and the associated `ZoneHVAC:EquipmentConnections` does not provide a matching exhaust/return node.
- As soon as the purchased-air model initializes, EnergyPlus treats the configuration as invalid and terminates.

### Impact
- Simulation stops before any HVAC sizing or time-step simulation occurs; no energy results are produced.

### Recommended Fix
1. Provide distinct zone inlet, exhaust, and return nodes (e.g., `{Zone} Supply Node`, `{Zone} Exhaust Node`, `{Zone} Return Node`).
2. If a return plenum is not being modeled, remove the plenum reference and wire the ideal loads system directly to the return node.
3. Re-run QA to confirm `InitPurchasedAir` completes without fatal errors.

---

## 1. Zone Equipment Node Naming Conflict (Critical)

### EnergyPlus Output
```
** Severe ** ZoneHVAC:EquipmentConnections="BUILDING_ZONE_1", duplicate node names found.
**   ~~~   ** ...Node Type(s)=Zone Air Inlet Nodes, duplicate node name="BUILDING_ZONE_1 SUPPLY NODE".
**  Fatal  ** GetZoneEquipmentData: Errors found in getting Zone Equipment input.
```

### Root Cause
- `ZoneHVAC:EquipmentConnections` defines both the zone air inlet and the zone air node using the same string (`Building_Zone_1 Supply Node`), which violates EnergyPlus node uniqueness rules.
- The emitted equipment list (e.g., `AirTerminal:SingleDuct:VAV:Reheat`, `ZoneHVAC:IdealLoadsAirSystem`) references that same node twice instead of providing a distinct zone air node.

### Impact
- `GetZoneEquipmentData` aborts before any HVAC sizing or simulation can begin.
- Downstream coil and load checks never run.

### Recommended Fix
1. Assign unique names for:
   - Zone air inlet node (`... Supply Inlet Node`)
   - Zone air node (`... Zone Air Node`)
   - Zone return node (`... Return Node`)
2. Update every zone HVAC component and terminal unit to reference the new node names consistently.
3. Re-run EnergyPlus; the `ZoneHVAC:EquipmentConnections` section should pass without duplication errors.

---

## 2. Window Orientation Mismatch (Critical)

### EnergyPlus Output
```
** Severe ** checkSubSurfAzTiltNorm: Outward facing angle of subsurface differs more than 90.0 degrees from base surface.
**   ~~~   ** Subsurface="BUILDING_ZONE_1_WINDOW_SOUTH" Tilt = 90.0  Azimuth = 0.0
**   ~~~   ** Base surface="BUILDING_ZONE_1_WALL_SOUTH" Tilt = 90.0  Azimuth = 180.0
```

### Root Cause
- Each exterior wall is emitted with coordinates consistent with `GlobalGeometryRules` (UpperLeftCorner, CounterClockWise, Relative).
- Matching `FenestrationSurface:Detailed` entries reuse the same vertex ordering without rotating it to the wall’s local coordinate system, effectively placing the window on the opposite face.

### Impact
- EnergyPlus stops during `GetSurfaceData` before sizing/autosizing, so no simulation output is generated.

### Recommended Fix
1. For every `FenestrationSurface:Detailed`, reorder vertices so the outward normal matches the parent wall’s outward direction.
2. Alternatively, emit window coordinates in the wall’s local coordinates using `Surface:HeatTransferAlgorithm` helpers or EnergyPlus geometry utilities.
3. Once corrected, rerun QA to confirm `GetSurfaceData` completes.

---

## 3. `Site:Location` Name Contains Commas (Critical)

### EnergyPlus Output
```
** Severe ** OutdoorAir:Node, duplicate Name = SITE OUTDOOR AIR NODE
**   ~~~   ** Duplicate Name might be found in an OutdoorAir:NodeList.
**  Fatal  ** Program terminates due to previously shown condition(s).
```

### Root Cause
- Generator defines `OutdoorAir:Node, SITE OUTDOOR AIR NODE;` once, but subsequent logic emits additional `OutdoorAir:Node` objects reusing the same name.
- EnergyPlus requires unique outdoor-air node names; duplicates cause the OA-node parsing routine to abort.
- Availability managers and outdoor air mixers continue to reference the shared name, so either a single shared node or unique per-loop nodes must be enforced consistently.

### Impact
- Simulation halts before sizing; no coils or loads are evaluated.
- Blocks verification of the coil fixes and EUI until resolved.

### Recommended Fix
1. Emit only one `OutdoorAir:Node` with the shared name, or give each loop a unique node name.
2. If a shared node is intended, stop creating duplicate `OutdoorAir:Node` entries; reference the same node via `OutdoorAir:NodeList` or direct node names.
3. If unique nodes are needed, rename them and update every `AvailabilityManager`, outdoor-air mixer, and DOAS component to match.
4. Re-run QA to confirm EnergyPlus passes OA-node validation.

**Reference:** EnergyPlus Input Output Reference, *OutdoorAir:Node* / *OutdoorAir:NodeList*, *AvailabilityManager:LowTemperatureTurnOff*.

---

## 4. `OutdoorAir:Node` Names Duplicated (Critical)

### EnergyPlus Output
```
** Severe ** Line: 106 Index: 0 - Object contains more field values than maximum number of IDD fields and is not extensible.
** Severe ** Line: 106 Index: 0 - Error parsing "Site:Location". Error in following line.
** Severe ** ~~~   200.0;                 !- Elevation
** Severe ** Line: 106 Index: 7 - "200.0" is not a valid Object Type.
**  Fatal  ** Errors occurred on processing input file. Preceding condition(s) cause termination.
```

### Root Cause
- The generator now sets site names to strings like `150 N Riverside Plaza, Chicago, IL 60606`.
- In IDF syntax commas separate fields; unescaped commas inside the name cause EnergyPlus to treat the remainder (`Chicago`, `IL 60606`, etc.) as additional fields, exceeding the object’s schema and leading to the fatal parse error.

### Impact
- EnergyPlus aborts before reading geometry or sizing data.
- Building area, lighting, and equipment metrics all report zero because the simulation never starts.

### Recommended Fix
1. Remove commas from name fields (e.g., use `150 N Riverside Plaza - Chicago IL`), or replace them with hyphens/underscores.
2. Alternatively, wrap the name in double quotes via the IDF text formatter so the commas are preserved safely.
3. Re-run QA to confirm the `Site:Location` object parses successfully.

**Reference:** EnergyPlus Input Output Reference, *Site:Location* object; IDF Editor rules on field separators.

---

## 5. DX Cooling Coils Producing Saturated Outlet Air (Critical)

### EnergyPlus Output
```
** Warning ** For object = Coil:Cooling:DX:SingleSpeed, name = "OFFICE_PRIVATE_0_Z6_COOLINGCOILDX"
**   ~~~   ** Calculated outlet air relative humidity greater than 1. The combination of rated air volume flow rate,
**   ~~~   ** total cooling capacity and sensible heat ratio yields coil exiting air conditions above the saturation curve.
... (repeats for every cooling coil during warmup) ...
```

### Root Cause
- Coil `Rated Total Cooling Capacity`, `Rated Air Flow Rate`, and `Rated Sensible Heat Ratio` are being set inconsistently.
- The resulting cooling coil bypass factor calculation drives the outlet state above saturation, forcing EnergyPlus to clamp SHR and throwing a warning for each coil every warmup/design step.
- Because capacities remain unrealistically high relative to airflow, latent/sensible splits remain invalid and downstream energy results will be unreliable.

### Impact
- Coil performance curves run outside valid envelope; psychrometric state is forced into saturation.
- Latent/sensible loads and EUI calculations remain untrustworthy even if the run completes.
- High warning volume (13+ per warmup step) masks other issues.

### Recommended Fix
- Size or autosize the trio of inputs together:
  1. Keep `Rated Air Flow Rate / Rated Total Cooling Capacity` within the EnergyPlus recommended band (2.684e‑5–6.713e‑5 m³/s·W).
  2. Pick a realistic `Rated Sensible Heat Ratio` (typically 0.70–0.75 for comfort cooling).
  3. Prefer letting EnergyPlus autosize all three using `autosize` so coil sizing reports stay internally consistent.
- After updating, validate via `eplusout.eio` (`DX Coil Standard Rating Information`) and ensure no saturation warnings remain.

**Reference:** EnergyPlus Engineering Reference, *Direct Expansion (DX) Cooling Coil Models*, section “Rated Conditions and Flow Ratios”.

---

## 6. Coil Frost / Outlet Air Temperatures Below −80 °C (Critical)

### EnergyPlus Output
```
** Warning ** ... Full load outlet temperature indicates a possibility of frost/freeze error continues.
**   ~~~   ** Outlet air temperature statistics follow:
**   ~~~   **   Max = -51.66 °C, Min = -82.61 °C
```

### Root Cause
- Direct consequence of the airflow/ton mismatch: excessive cooling capacity applied to tiny air volumes forces the calculated outlet temperature deep below freezing.
- No minimum outlet temperature or defrost control is defined for the coils.

### Impact
- Unrealistic supply-air conditions (impossible in real systems).
- Causes `PsyWFnTdbH` to receive negative humidity ratios.
- Means the coil is not delivering usable sensible cooling.

### Recommended Fix
1. **Apply fix #1 (coil sizing).** That alone should raise outlet temperatures to ~12 °C.
2. Add operating limits to each `Coil:Cooling:DX:SingleSpeed` object:
   ```idf
   Coil:Cooling:DX:SingleSpeed,
     ...,                                 !- Name
     ...,                                 !- Rated Total Cooling Capacity
     ...,                                 !- Rated Sensible Heat Ratio
     ...,                                 !- Rated Air Flow Rate
     5,                                   !- Minimum Outdoor Dry-Bulb Temperature for Compressor Operation {C}
     ...
   ```
3. Optionally set `UnitarySystemPerformance:Multispeed` or `CoilSystem:Cooling:DX:HeatPump` with defrost control if heating mode shares the same coil.

**Reference:** EnergyPlus Input Output Reference, *Coil:Cooling:DX:SingleSpeed – Minimum Outdoor Dry-Bulb Temperature field*; Engineering Reference, *Coil Frost Control*.

---

## 7. Low Condenser Dry-Bulb Temperature (High Priority)

### EnergyPlus Output
```
** Warning ** CalcDoe2DXCoil ... - Low condenser dry-bulb temperature error continues...
**   ~~~   ** Max=-0.025 °C, Min=-3.30 °C
```

### Root Cause
The service creates air-cooled DX condensers but allows them to run below 0 °C outdoor temperature where the model requires defrost logic or cut-off.

### Impact
- The default EnergyPlus curve data is invalid in this regime; results are unreliable.

### Recommended Fix
- After implementing #1 and #2, set the cut-off temperature (as shown above). If sub-freezing operation is necessary, switch to `CoilSystem:Cooling:DX:HeatPump` with `Defrost Strategy` = `ReverseCycle` and provide defrost curves (Engineering Reference, *Heat Pump Coil Defrost*).

---

## 8. Psychrometric Failure – `Calculated Humidity Ratio invalid (PsyWFnTdbH)` (High Priority)

### EnergyPlus Output
```
** Warning ** Calculated Humidity Ratio invalid (PsyWFnTdbH)
**   ~~~   ** This error occurred 228954 total times; Max=-0.000101, Min=-0.009350
```

### Root Cause
PsyWFnTdbH expects enthalpy/temperature pairs within the saturation envelope. Because the coil outlet state is below −50 °C, the calculated humidity ratio becomes negative, triggering the warning.

### Impact
- Humidity, latent loads, and comfort metrics are meaningless.

### Recommended Fix
- Resolves automatically once items 1–3 are addressed. No separate change is needed if the coil outputs return to realistic values.

**Reference:** EnergyPlus Engineering Reference, *Psychrometric Calculations*.

---

## 9. Energy Use Intensity ≈ 0.52 kWh/m²·year (Medium Priority)

### Observation
- After local parsing fixes, every scenario reports EUI ≈ 0.52–0.53 kWh/m²·year.
- A typical ASHRAE-90.1 compliant medium office should land between 50–200 kWh/m²·year (DOE reference buildings, ASHRAE 90.1 Appendix G).

### Root Causes
1. Cooling coils deliver essentially zero sensible load due to previous issues.
2. Heating equipment may be missing or inactive (no `Coil:Heating:*` or `Boiler` objects present in the generated IDFs).
3. Schedules likely keep the building at min-load.

### Recommended Fix
1. **After repairing coil sizing**, rerun simulations; EUI should rise substantially.
2. Verify the service outputs heating components (gas, electric or district heat) and thermostats with realistic setpoints (e.g. 21 °C occupied, 15 °C setback).
3. Adopt realistic occupancy, lighting, and equipment schedules. DOE/ASHRAE medium office schedules are published in the EnergyPlus example `RefBldgMediumOfficeNew2004_Chicago.idf` and in ASHRAE 90.1 Appendix G.
4. Run EnergyPlus autosizing (`Sizing:Zone`, `Sizing:System`, `Sizing:Plant`) to confirm design loads are met.

---

## Recently Resolved (Keep in Regression Suite)
- `SizingPeriod:DesignDay` objects now use valid `WinterDesignDay`/`SummerDesignDay` enums and parse correctly (verified 7 Nov 2025 15:25 UTC).
- `Sizing:System` objects now include the mandatory temperature/humidity fields (verified 7 Nov 2025 15:29 UTC).

---

## Next Steps
1. Implement fixes 1–5 in the IDF generation pipeline.
2. Notify us when deployed; we will immediately re-run the 5-address validation suite.
3. Once warnings disappear and EUI is in a realistic range, we can proceed to final acceptance.

---

### Key References
- EnergyPlus Input Output Reference (v24.2.0): *Coil:Cooling:DX:SingleSpeed*, *ThermostatSetpoint*, *Sizing:* objects.
- EnergyPlus Engineering Reference (v24.2.0): *DX Cooling Coils*, *Psychrometric Functions*, *Heat Pump Defrost*.
- DOE Reference Buildings: Medium Office (for schedules & target EUIs).




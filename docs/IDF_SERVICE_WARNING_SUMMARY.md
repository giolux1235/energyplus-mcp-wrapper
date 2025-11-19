# IDF Creator Warning Summary – 8 Nov 2025

Source run: `test_outputs/test_5_1762636437480/` (address `150 N Riverside Plaza, Chicago, IL 60606`) generated via `comprehensive-idf-test.mjs`.

---

## 1. Geometry & Loads

- `Inside surface heat balance did not converge ...` (41 occurrences; max delta 25.94 °C)
- `Temperature (high) out of bounds 230.8 °C for BUILDING_ZONE_1_FLOOR`
- `Temperature (low) out of bounds –164.8 °C for BUILDING_ZONE_1_CEILING`
- `Temperature (low) out of bounds –267.5 °C for BUILDING_ZONE_1_FLOOR`

**Impact:** The zone blows up thermally during early April hours; EnergyPlus aborts with severe temperature excursions, so no trustworthy loads or energy metrics are produced.

**Suggested fix:** Validate wall/roof constructions (add thermal mass), ensure realistic internal gains and schedules, and correct HVAC control strategy before rerunning.

---

## 2. Schedules & Internal Gains

- `ProcessScheduleInput: Schedule:Compact="PEOPLE OCCUPANCY SCHEDULE" has missing day types in Through=12/31 (Holiday)`
- Same warning for `EQUIPMENT SCHEDULE`
- `GetInternalHeatGains: Lights="BUILDING_ZONE_1_LIGHTS"... field blank → 0 lights`
- `GetInternalHeatGains: ElectricEquipment="BUILDING_ZONE_1_EQUIPMENT"... field blank → 0 equipment`

**Impact:** Occupancy, lighting, and equipment schedules go to zero on holidays; combined with blank watts/m² fields, the building runs without internal gains, worsening the thermal instability.

**Suggested fix:** Provide complete day-type coverage in each `Schedule:Compact` and fill in the load intensity fields.

---

## 3. HVAC & Node Connections

- `SetUpZoneSizingArrays: Zone ... has no thermostat`
- `Calculated design cooling/heating load ... is zero`
- `InitPurchasedAir: ZoneHVAC:IdealLoadsAirSystem cannot find ZoneHVAC:ReturnPlenum`
- `ZoneHVAC:EquipmentConnections`: exhaust node has no matching inlet
- `ZoneHVAC:IdealLoadsAirSystem`: inlet node “50” not registered in `OutdoorAir:Node/List`

**Impact:** Zone sizing is bypassed, the ideal loads system lacks proper node hookups, and EnergyPlus reports fatal node connection errors before any meaningful simulation.

**Suggested fix:** Provide `ZoneControl:Thermostat`, ensure each ZoneHVAC component references distinct inlet/exhaust/return nodes, and register all OA nodes properly.

---

## 4. Recurring Warning Summary (EnergyPlus footer)

- `Inside surface heat balance convergence problem continues` (41 total; max delta 17.04 °C)
- `EnergyPlus Terminated--Fatal Error Detected. 61 Warning; 7 Severe Errors`

---

### Next Steps for IDF Creator Team
1. Fix thermostat, node connectivity, and ideal loads references so `ZoneHVAC:EquipmentConnections` passes validation.
2. Correct schedules and load definitions to reintroduce realistic internal gains.
3. Address thermal instability (construction mass, control strategy) to eliminate temperature out-of-bounds.
4. Re-export sample IDFs and notify QA; we will rerun the 5-address validation suite.


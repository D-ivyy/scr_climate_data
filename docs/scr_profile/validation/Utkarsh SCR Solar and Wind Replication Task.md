# Utkarsh task — replicate the SCR gas test for Solar PV and Onshore Wind

## Objective

Repeat the completed 146-location gas-fired generation SCR test for two asset classes while holding every other input constant:

1. Photovoltaic generation — TICCS `IC702010`.
2. Onshore wind — TICCS `IC701010`.

The purpose is to determine whether SCR's overall and hazard-specific physical-damage results materially change by asset class at the same locations.

## Required location input

Use every row in:

```text
docs/scr_profile/validation/2026-08-05_gas_146_location_manifest.csv
```

Requirements:

- Use exactly 146 rows.
- Use the supplied `lat_center` and `lon_center` without rounding or moving the point.
- Preserve `cell_id`, state, and ISO/RTO in the run manifest.
- Do not select a different nearby coordinate or known operating asset.
- The same cell must be present once for Solar PV and once for Onshore Wind.

## Inputs that must remain controlled

| Input | Required value |
| --- | --- |
| Country | United States |
| Asset value | $10,000,000 |
| Annual revenue | $1,000,000 |
| Solar classification | Photovoltaic generation / `IC702010` |
| Wind classification | Onshore wind / `IC701010` |
| Scenarios | SSP2-4.5 and SSP5-8.5 |
| Horizons | Keep the full SCR export: Historical and 2025–2100 |
| Adaptation/resilience inputs | Use the same default/no-measure setting as the gas reference run |
| Output | Physical-risk CSV and XLSX exports |

Do not change value or revenue by asset class during this controlled test. That would mix asset-class effects with financial-input effects.

## Execution sequence

```text
146-location manifest
        |
        +---- create 5 Solar PV assets ---- export and inspect
        |
        +---- create 5 Onshore Wind assets ---- export and inspect
        |
        v
confirm taxonomy, coordinates, scenarios, and workbook format
        |
        +---- finish all 146 Solar PV locations
        +---- finish all 146 Onshore Wind locations
        |
        v
deliver raw exports + completed run manifests
```

Use the five-location check before the complete batch so a wrong TICCS subclass or input convention is not replicated 292 times.

## Naming convention

Use a deterministic name that keeps the cell ID visible. Suggested names:

```text
Cell_<cell_id>_<state>_<iso>_SolarPV
Cell_<cell_id>_<state>_<iso>_OnshoreWind
```

If the portal restricts characters or length, document the final naming rule and provide a manifest mapping each SCR `assetId` and `assetName` back to `cell_id` and asset class.

## Required delivery

Deliver the following without writing an executive summary:

1. One ZIP containing all 146 Solar PV CSV/XLSX export pairs.
2. One ZIP containing all 146 Onshore Wind CSV/XLSX export pairs.
3. A completed manifest for each asset class with:
   - `cell_id`;
   - submitted latitude and longitude;
   - SCR `assetId`;
   - SCR `assetName`;
   - asset type;
   - TICCS subclass and name;
   - asset value and revenue;
   - export/report date;
   - export status and any error note.
4. A short exception list covering any cell that could not be created or exported.

Suggested internal filenames:

```text
solar_pv_physical_risk_data.zip
onshore_wind_physical_risk_data.zip
solar_pv_146_run_manifest.csv
onshore_wind_146_run_manifest.csv
```

Do not distribute the raw SCR exports outside the authorized team. The workbook disclaimer contains redistribution restrictions.

## Acceptance checks before handoff

For each asset class:

- 146 unique `cell_id` values.
- 146/146 coordinates equal the supplied cell centers.
- No duplicate cell-and-asset pair.
- 146 CSV files and 146 matching XLSX files, unless an exception is documented.
- One consistent asset classification across all locations.
- One consistent asset value and revenue across all locations.
- Both scenarios returned.
- Historical plus 2025–2100 horizons returned.
- Raw exports preserved without manual edits.

The analysis team will then run the same checks used for Gas:

- overall `adjustedTotalDamage` baseline and future coverage;
- overall physical-damage factor distribution;
- hazard-level indicator and damage coverage;
- valid hazard-specific factor coverage;
- sum of hazard damage versus total damage;
- raw versus adjusted field differences;
- missing, zero, and near-zero baselines;
- extreme-factor and absolute-movement review;
- comparison against Gas at the same cell IDs.

## Completion condition

The task is complete when the two raw export sets and their manifests pass the acceptance checks or every exception is explicitly listed. The full 13,085-cell run is not part of this task.

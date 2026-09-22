---
author: InfraSure
created: 2026-09-21
updated: 2026-09-22
status: active investigation
---

# SCR Solar + Wind physical and transition expansion

## Why this workstream exists

InfraSure's first SCR implementation covered one quadrant: Solar photovoltaic
physical damage. The source collection now supports a two-asset, two-risk-family
investigation:

```text
                              SCR risk family
                    Physical damage       Transition risk
                  +--------------------+--------------------+
 Solar PV         | EXISTING DELIVERY  | NEW INVESTIGATION  |
                  | validate refresh   | profile + design   |
                  +--------------------+--------------------+
 Onshore wind     | RESEARCH COMPLETE  | NEW INVESTIGATION  |
                  | filled V1/V2 + QA  | profile + design   |
                  +--------------------+--------------------+

Execution order: inventory -> Wind physical -> transition semantics ->
                 transition packages -> delivery/dashboard integration
```

The two risk families must remain conceptually separate:

```text
SCR physical damage change
    -> candidate modifier for InfraSure physical expected loss (EAL)

SCR transition indicators, impacts, and ratings
    -> scenario-based revenue / OpEx / cash-flow stress and screening
    -> not a physical-loss multiplier
```

## What is already complete

The existing Solar physical recipient release is a canonical-grid package with:

- 13,085 cells;
- two SSP scenarios;
- 16 five-year future horizons from 2025 through 2100;
- 418,720 rows (`13,085 x 2 x 16`);
- observed and nearest-neighbor-filled provenance; and
- a stabilized overall `adjustedTotalDamage` factor intended only for EAL.

That release remains the current implementation baseline. The newly discovered
Solar workbooks are a newer upstream source surface and must not silently replace
the released package.

The Wind physical research package is also complete. It contains a raw field
that preserves SCR's unsupported factors as null and a separate complete-grid
field filled from the nearest metric-eligible Wind cell. Stabilization is
applied only after that separation, so observed SCR, imputation, and numerical
guardrails remain independently auditable.

## Current GCS source inventory

Inventory date: 2026-09-21.

Canonical grid:

`gs://infrasure-benchmark/hazard_conus_grid/dev/common/benchmark_grid/served_conus_cell_ids_v2026_06.csv`

| Asset | Risk family | GCS prefix | XLSX files | Canonical cells | Missing |
|---|---|---|---:|---:|---:|
| Solar PV | Physical | `gs://infrasure-scr-data/Solar-asset/physical_risk/` | 13,041 | 13,041 | 44 |
| Solar PV | Transition | `gs://infrasure-scr-data/Solar-asset/transition_risk/` | 13,041 | 13,041 | 44 |
| Onshore wind | Physical | `gs://infrasure-scr-data/onshore_wind/physical_risk/` | 13,085 | 13,085 | 0 |
| Onshore wind | Transition | `gs://infrasure-scr-data/onshore_wind/transition_risk/` | 13,085 | 13,085 | 0 |

Observed reconciliation:

- all four prefixes contain unique, filename-readable cell IDs;
- no prefix contains a noncanonical cell;
- Solar physical and Solar transition contain exactly the same cell set;
- the same 44 Solar cells are absent from both risk families; and
- both Wind prefixes equal the complete canonical 13,085-cell set.

This means the Solar shortfall is already present in SCR's raw exports. It is
not caused by InfraSure parsing, joining, or filtering.

## Initial workbook findings

These findings come from direct inspection of current GCS workbooks. They are
based on seven deterministic cells per surface (28 workbooks total), spanning
the ordered cell range. They are not yet a full-corpus content validation.

Across those 28 workbooks:

- no sampled workbook was missing its `Output` sheet;
- every sampled source-grain key was unique;
- all seven workbooks within each surface had one shared header hash;
- Solar and Wind physical workbooks shared the same header hash;
- Solar and Wind transition workbooks shared the same header hash; and
- repeated overall-damage and subrisk-impact measures were internally
  consistent within their expected grouping keys.

The order of physical indicator rows varied between some workbooks even though
the indicator set was identical. Production parsing must therefore use named
columns and explicit keys, never fixed row positions.

### Physical exports

Solar and Wind samples share the same 36-column `Output` schema and contain:

- 986 rows per workbook;
- scenarios `ssp2-4.5` and `ssp5-8.5`;
- `Historical` plus 2025-2100 at five-year intervals;
- 29 indicators; and
- nine hazards: Drought, Earthquake, Flood, Heat, Landslide, Precipitation,
  Subsidence, Wildfire, and Wind.

The new exports therefore add Earthquake / peak ground acceleration relative
to older profile notes that described 28 indicators and eight hazards.

Solar is identified as TICCS `IC702010`, Photovoltaic Power Generation. Wind is
identified as TICCS `IC701010`, On-Shore Wind Power Generation.

### Transition exports

Solar and Wind samples share the same 20-column `Output` schema and contain:

- 216 rows per workbook;
- nine scenario pathways;
- six horizons: 2025, 2030, 2035, 2040, 2045, and 2050;
- four indicators: Carbon price, Revenue growth, Scope 1+2 emissions intensity,
  and Scope 3 emissions intensity; and
- two subrisks: Direct Carbon Cost and Market Demand Shifts.

The nine observed pathways are:

1. Below 2°C
2. Climate Breakdown
3. Climate Destabilization
4. Current Policies
5. Delayed transition
6. Expected
7. Fragmented World
8. Nationally Determined Contributions (NDCs)
9. Net Zero 2050

This differs materially from the older local examples, which described six
pathways, horizons through 2060, five indicators, and an Inflation indicator.
The current GCS contract must therefore be profiled from source rather than
inferred from the older examples.

## Resolved decisions and remaining questions

### Wind physical

1. All 13,085 Wind physical workbooks share one validated output schema and
   parsed without error.
2. `adjustedTotalDamage` supports a complete factor path at 11,968 cells; 1,117
   cells lack a usable 2025 baseline even though their workbooks exist.
3. Raw Wind factors have the same tiny-baseline ratio-tail failure mode seen in
   Solar; the tested 3x/5x arctangent method changes only 307 observed rows.
4. The applied research surface uses the nearest metric-eligible Wind donor for
   the 1,117 unsupported cells while preserving raw nulls and donor provenance.
5. The filled V2 changes 308 rows: the same 307 observed tail rows plus one
   copied donor-path row.

### Transition risk

These remain open and define the next investigation phase:

1. Does an adjusted subrisk impact of `-17.0353` mean `-17.0353%`, or is a
   different scale intended?
2. What is the exact denominator for Direct Carbon Cost and Market Demand
   Shifts: revenue, OpEx, or a subrisk-specific base?
3. Can the two subrisk impacts be combined, and if so, by what rule?
4. Are 2025 blanks structural baselines rather than missing data?
5. Are indicators country/scenario constants while impacts and ratings vary by
   asset class, or is there meaningful cell-level variation?
6. Should InfraSure deliver transition data as a rating-only screen first, or
   can validated impact values become direct cash-flow stresses?

## Working guardrails

- Do not combine physical and transition risk into one score.
- Do not apply transition impacts to physical EAL.
- Do not convert transition impacts to dollars until unit, sign, denominator,
  and duplication semantics are validated.
- Do not assume Solar stabilization parameters are correct for Wind without a
  full-distribution comparison.
- Do not overwrite raw SCR values. Derived, stabilized, or imputed fields must
  remain separate and traceable.
- Do not change the current Solar physical release until the new source surface
  has passed a controlled comparison.

## Evidence and next artifact

Reproducible inventory and sample-schema profiling lives under
[`notebooks/scr_four_surface_inventory/`](../../../../notebooks/scr_four_surface_inventory/).
The completed Wind physical investigation is documented in
[`01_wind_physical_full_corpus_findings.md`](01_wind_physical_full_corpus_findings.md).
The reviewed completion decision and immutable package are documented in
[`02_wind_nearest_fill_implementation.md`](02_wind_nearest_fill_implementation.md).
The ordered implementation is defined in the
[`SCR Solar and Wind Physical and Transition Expansion Plan`](../../plans/SCR%20Solar%20and%20Wind%20Physical%20and%20Transition%20Expansion%20Plan.md).

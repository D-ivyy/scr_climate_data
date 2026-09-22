---
author: InfraSure
created: 2026-09-22
updated: 2026-09-22
status: local research trial implemented and validated; no production financial release authorized
scope: Apply SCR Direct Carbon Cost and Market Demand impacts separately and additively as provisional percentage-point adjustments to accepted Solar/Wind V6 annual revenue, then test the three screening views in the Hazard Modeling Delivery map before full expansion.
---

# SCR transition revenue application and dashboard trial plan

## Implementation status — 2026-09-22

The local research trial is implemented end to end.

```text
SCR Solar + Wind transition workbooks
                 +
accepted V6 Solar + Wind revenue Parquets
                 |
                 v
scripts/build_transition_revenue_screening.py
                 |
                 +-- full trial Parquet (1,413,180 rows)
                 +-- run manifest + QA report
                 +-- compact dashboard grid/template bundle
                 |
                 v
Hazard Modeling Delivery dashboard
  [ Current loss ] [ Physical climate ] [ Transition screen ]
```

Completed checks:

- `2 assets x 13,085 cells x 9 scenarios x 6 horizons = 1,413,180 rows`;
- no duplicate analytical grain;
- no parsing failures in the selected source templates;
- raw and adjusted SCR impacts are identical wherever populated in the current
  source corpus;
- additive impact, factor, and adjusted-revenue formulas reconcile exactly;
- 44 missing Solar SCR cells and two missing Wind revenue cells remain explicit
  nulls;
- dashboard unit tests, lint, TypeScript compilation, and production build pass;
  and
- default, alternate scenario/driver/horizon, and unavailable-cell states were
  visually inspected in the local dashboard.

Primary implementation artifacts:

```text
scripts/build_transition_revenue_screening.py
runs/transition_revenue_screening/run_id=20260922T160000Z/
  scr_transition_revenue_screening_conus.parquet
  manifest.json
  qa_report.json
  README.md

/Users/divy/code/work/infrasure_git_codes/Hazard_modeling/dashboard/
  components/delivery-transition.tsx
  lib/delivery-transition.ts
  lib/server/delivery-data.ts
  app/api/delivery/transition/{slice,cell}/route.ts
```

This completes the **local trial**, not production promotion. No production
`current.delivery.yml` pointer was changed.

## Decision in one screen

Build a narrow, reversible transition-risk trial using the assumption that SCR
numeric impact values are percentage points.

```text
Accepted V6 grid-cell revenue                 SCR transition profile
Solar: 13,085 cells                           9 scenarios x 6 horizons
Wind:  13,083 cells                           2 subrisk impacts + ratings
              \                              /
               \ exact cell_id + asset join /
                +---------------------------+
                              |
                              v
           Three annual-revenue screening views
           + Direct Carbon + Market Demand + additive overall
                              |
                              v
              Hazard Modeling Delivery map trial
```

The trial makes one temporary interpretation:

```text
SCR impact value 2.045696 -> 2.045696 percentage points
```

The raw SCR value remains unchanged. The assumption is stored in an explicit
field and must be revisited before a governed production financial release.

## What is in scope

1. Join SCR Solar and Wind transition results to the accepted V6 revenue layer.
2. Apply `Market Demand Shifts` to baseline annual revenue.
3. Apply `Direct Carbon Cost` to the same annual-revenue base as an explicitly
   temporary proxy while preserving the future OpEx-denominator caveat.
4. Calculate an additive same-base overall transition screening factor.
5. Produce an auditable trial Parquet at
   `cell_id x asset_type x scenario x horizon` grain.
6. Test Generation, Baseline Revenue, Direct Carbon, Market Demand, Overall
   Transition, and Revenue Change on the existing Hazard Modeling Delivery map.
7. Make units, assumptions, source regime, missingness, and research status
   visible and accessible.

## What is intentionally deferred

- confirming SCR's percentage scale, denominator, sign, and time semantics;
- replacing the temporary Direct Carbon revenue proxy with validated OpEx or
  cash-flow treatment;
- promoting the additive overall screening factor into a governed cash-flow
  factor;
- outlier compression, winsorization, caps, floors, or logarithmic treatment;
- spatially filling the 44 missing Solar SCR transition cells;
- repairing the two missing Wind revenue cells;
- treating the Wind template boundary as geographic transition variation; and
- updating a production `current.delivery.yml` pointer.

Outliers remain raw and visible in the trial. Any later stabilization decision
must be supported by a separate distribution and financial-sensitivity review.

## Baseline revenue authority and version finding

The current stable revenue aliases are:

```text
/Users/divy/code/personal/renewablesinfo/products/index_analysis_lab/
  data/delivery/solar_revenue_layer_conus.parquet
  data/delivery/wind_revenue_layer_conus.parquet
```

The delivery README maps them to the accepted internal V6 products:

```text
solar_revenue_layer_conus.parquet -> data/outputs/solar_revenue_v6.parquet
wind_revenue_layer_conus.parquet  -> data/outputs/wind_revenue_v6.parquet
```

Local byte comparisons confirm that each stable alias is identical to its V6
source artifact.

| Asset | Rows / unique cells | Columns | Primary revenue nulls | SHA-256 |
|---|---:|---:|---:|---|
| Solar | 13,085 | 162 | 0 | `fe7fcc9933439bfefd23fdaf451cba9d8a0e45505471ef29e1caa92460f2340c` |
| Wind | 13,083 | 167 | 0 | `4226cbf4c8c2a8ea4e51f3b0120c83a0d2da9b0ce473cf5f04db4767a3051d96` |

Primary revenue fields:

```text
annual_revenue_adj_curtailment_market_value_p75_usd_kwp_yr
annual_revenue_adj_curtailment_market_value_p75_100mw_usd_yr
```

The current weakness is version governance, not the revenue calculation:

- neither Parquet contains a version, release ID, run ID, or generated-time
  column;
- the stable filenames deliberately omit versions; and
- no revenue `current.delivery.yml` or three-file sidecar package was found in
  this source delivery folder.

For the trial, pin the exact file SHA-256 values above in the run manifest. A
production release should later place the stable names behind a governed
release pointer and sidecar rather than inferring V6 from a README.

## Join coverage and missingness

The trial uses an explicit left/outer reconciliation, never silent row loss.

| Asset | Revenue cells | SCR transition cells | Expected matched cells | Required treatment |
|---|---:|---:|---:|---|
| Solar | 13,085 | 13,041 | 13,041 | Preserve 44 cells as `scr_transition_unavailable`; do not spatially fill |
| Wind | 13,083 | 13,085 | 13,083 | Preserve revenue-unavailable status for cells `327842` and `376954` |

Every canonical cell must receive one of these statuses:

```text
matched
scr_transition_unavailable
baseline_revenue_unavailable
structural_subrisk_null
```

A missing value is never converted to zero, `1x`, or a nearest-neighbor value.

## Financial application contract

Let:

```text
R0 = accepted V6 baseline annual revenue
m  = SCR adjusted Market Demand Shifts source value
d  = SCR adjusted Direct Carbon Cost source value
```

Trial calculations:

```text
direct_carbon_fraction = d / 100
direct_carbon_factor = 1 + direct_carbon_fraction
direct_carbon_revenue_delta = R0 x direct_carbon_fraction
direct_carbon_adjusted_revenue = R0 x direct_carbon_factor

market_demand_fraction = m / 100
market_demand_factor = 1 + market_demand_fraction
market_demand_revenue_delta = R0 x market_demand_fraction
market_demand_adjusted_revenue = R0 x market_demand_factor

overall_transition_impact = d + m
overall_transition_fraction = overall_transition_impact / 100
overall_transition_screening_factor = 1 + overall_transition_fraction
overall_transition_revenue_delta = R0 x overall_transition_fraction
overall_transition_adjusted_revenue = R0 x overall_transition_screening_factor
```

Actual Wind Template B example for `cell 267458 · MN`, `Expected`, 2030:

```text
R0 = $2,234,525.14 / year for the V6 standardized 100 MW project
d  = -0.001872
m  = +2.045696

direct_carbon_factor = 0.99998128x
market_demand_factor = 1.02045696x
overall_transition_impact = +2.043824
overall_transition_screening_factor = 1.02043824x

direct_carbon_revenue_delta = approximately -$41.83 / year
market_demand_revenue_delta = approximately +$45,711.59 / year
overall_transition_revenue_delta = approximately +$45,669.76 / year
overall_transition_adjusted_revenue = approximately $2,280,194.90 / year
```

Direct Carbon Cost uses annual revenue only as a disclosed trial proxy:

```text
direct_carbon_cost_source_value = d
direct_carbon_cost_source_unit = "%" [SCR-declared]
direct_carbon_cost_application_status = "experimental_annual_revenue_proxy"
```

Do not apply `d` or `m` to TIV. Do not add Scope 3 intensity, revenue growth,
carbon price, or Scope 1+2 intensity a second time; they are explanatory
indicators, not additional adjustment factors.

The calculated numeric overall factor is an InfraSure trial field. It is not
SCR's supplied `overallTransitionRating`, which remains a separate A-G category.

## Trial Parquet contract

Recommended stable trial filename:

```text
scr_transition_revenue_screening_conus.parquet
```

Scientific and run identities belong in the run manifest and columns, not in
the filename.

Grain:

```text
cell_id x asset_type x scenario x horizon
```

Expected matched-row counts before unavailable-cell scaffold rows:

```text
Solar: 13,041 x 9 x 6 = 704,214
Wind:  13,083 x 9 x 6 = 706,482
```

Required field groups:

### Identity and geography

```text
cell_id
lat_center
lon_center
state_abbr
asset_type
ticcs_subclass
```

### Scenario identity

```text
scenario
horizon
scr_report_date
scr_source_regime
```

### SCR explanatory indicators

```text
carbon_price
carbon_price_unit
scope_1_2_intensity
scope_1_2_intensity_unit
revenue_growth
revenue_growth_unit
scope_3_intensity
scope_3_intensity_unit
```

### SCR model outputs

```text
direct_carbon_cost_impact_raw
direct_carbon_cost_impact_adjusted
direct_carbon_cost_rating
market_demand_impact_raw
market_demand_impact_adjusted
market_demand_rating
overall_transition_rating
```

### Accepted baseline economics

```text
p75_generation_kwh_kwp_yr
baseline_revenue_usd_kwp_yr
baseline_revenue_100mw_usd_yr
baseline_revenue_method_version       = "V6"
baseline_revenue_source_sha256
```

### Trial-derived fields

```text
direct_carbon_fraction
direct_carbon_factor
direct_carbon_revenue_delta_usd_kwp_yr
direct_carbon_revenue_delta_100mw_usd_yr
direct_carbon_adjusted_revenue_usd_kwp_yr
direct_carbon_adjusted_revenue_100mw_usd_yr
market_demand_fraction
market_demand_factor
market_demand_revenue_delta_usd_kwp_yr
market_demand_revenue_delta_100mw_usd_yr
market_demand_adjusted_revenue_usd_kwp_yr
market_demand_adjusted_revenue_100mw_usd_yr
overall_transition_impact
overall_transition_fraction
overall_transition_screening_factor
overall_transition_revenue_delta_usd_kwp_yr
overall_transition_revenue_delta_100mw_usd_yr
overall_transition_adjusted_revenue_usd_kwp_yr
overall_transition_adjusted_revenue_100mw_usd_yr
```

### Interpretation and QA

```text
impact_scale_assumption               = "source_value_is_percentage_points"
market_demand_application_status      = "experimental_revenue_screen"
direct_carbon_application_status      = "experimental_annual_revenue_proxy"
overall_combination_method            = "additive_same_revenue_base_proxy"
tiv_application_status                = "not_applied"
join_status
source_uri
pipeline_version
created_at_utc
```

Raw SCR values must remain available even when a derived field is null.

## Dashboard placement

The target is the existing Hazard Modeling **Delivery** map, not the standalone
SCR workbook-inspection dashboard.

Keep three reader questions separate:

```text
[ Current loss ] [ Physical climate ] [ Transition screen ]
```

- `Current loss`: existing governed hazard EAL and tails.
- `Physical climate`: existing SCR physical factor applied to EAL.
- `Transition screen`: revenue/generation context plus SCR transition impacts
  and ratings.

Transition must not appear as another physical hazard.

## Minimal transition-screen experience

### Global controls

```text
Asset:    Solar PV | Onshore Wind
Scenario: 9 SCR transition pathways
Horizon:  2025 | 2030 | 2035 | 2040 | 2045 | 2050
```

### Map metric

```text
P75 generation
Baseline V6 revenue
Adjusted revenue
Revenue change
Applied screening factor
SCR subrisk / overall rating
```

Add one driver selector:

```text
Direct Carbon | Market Demand | Overall
```

The default trial view should be `Overall / Adjusted revenue`, with
`Expected / 2030` as the initial review slice. Generation and Baseline Revenue
remain adjacent reference layers so the user can understand where the dollar
pattern originates. `Overall` means the InfraSure additive numeric screen; the
SCR overall A-G rating keeps the explicit label `SCR overall rating`.

Do not default to a map of raw SCR Market Demand impacts: Solar is constant
across observed cells, and Wind contains two source regimes. A raw-impact map
could imply geographic variation that the source does not establish.

### Selected-cell panel

```text
Cell identity and location
Asset type and SCR source regime

Generation
  P75 generation

Baseline economics
  V6 revenue $/kWp/year
  V6 standardized 100 MW revenue

Direct Carbon screening
  SCR source value and declared unit
  annual-revenue proxy factor
  revenue-proxy delta
  adjusted revenue proxy
  Direct Carbon rating

Market Demand screening
  SCR source value and declared unit
  factor
  revenue delta
  adjusted revenue
  Market Demand rating

Overall transition screening
  additive combined impact
  additive factor
  combined revenue delta
  combined adjusted revenue
  "Experimental — Direct Carbon may ultimately require OpEx"

SCR overall transition rating
Source, assumption, and missingness details
```

The calculation must be visible as a short trace:

```text
$33.53/kWp/year
x 1.02045696
= $34.22/kWp/year
```

## Map interpretation copy

Place one concise explanation near the first transition map:

> Geographic variation in adjusted revenue primarily comes from InfraSure's
> baseline generation and revenue layer. SCR transition impacts are currently
> repeated by asset/scenario profile rather than demonstrated as a continuous
> location-specific surface.

For Wind, display a source-regime label until the Template A / Template B
boundary is explained. Do not label that boundary as higher or lower local
transition exposure.

## Accessibility contract

1. All selectors and view toggles use native keyboard-operable controls with
   visible labels and focus indicators.
2. Every selected cell is reachable without hover; selection changes announce
   the cell, active scenario, horizon, metric, and value through a polite live
   region.
3. Provide a table/list alternative for exact cell lookup and sorting.
4. Legends contain units, endpoints, and a missing/unavailable category. Never
   communicate rating or direction through color alone.
5. Information controls are focusable and explain percentage assumption,
   baseline source, Direct Carbon revenue-proxy caveat, additive combination,
   and source regime.
6. Tooltips are available on focus and touch, not only mouse hover.
7. Preserve raw values and useful precision in details while keeping map labels
   rounded and readable.
8. Structural nulls and unavailable joins have text labels and distinct
   patterns, not silent blank or zero-colored cells.

## Serving architecture

The browser should not read Parquet or perform the financial calculation.

```text
Pinned SCR transition extraction
        +
Pinned V6 revenue Parquets
        |
        v
trial builder
  - validate hashes and grains
  - reconcile cell coverage
  - calculate Direct Carbon, Market Demand, and additive overall screens
  - emit Parquet + manifest + QA
        |
        v
Hazard Modeling dashboard exporter
  - verify trial package
  - produce asset/scenario/horizon map slices
  - produce selected-cell dossiers
        |
        v
Next.js APIs
  /api/delivery/transition/slice
  /api/delivery/transition/cell
        |
        v
Delivery transition-screen reader
```

This mirrors the existing physical-climate architecture: calculations and
validation happen before the browser; React selects and renders reviewed data.

## Execution phases

### T0 — Freeze the trial contract

- approve the percentage-point assumption for research use;
- pin both V6 revenue SHA-256 values;
- pin the SCR transition run, inventory hash, and source fingerprints;
- record the four join statuses; and
- add unit and application-status definitions.

Gate: the same source bytes and formula reproduce one Solar and one Wind
Expected/2030 example by hand.

### T1 — Build one-slice trial data

- build `Expected / 2030` for Solar and Wind only;
- calculate Direct Carbon, Market Demand, and additive overall factors,
  adjusted-revenue proxies, and deltas;
- reconcile 13,041 Solar and 13,083 Wind matched cells; and
- produce a QA summary of factors, revenue deltas, nulls, and source regimes.

Gate: no duplicate grain, no silent row loss, no invalid factor where Market
Demand or Direct Carbon is null, and selected examples reconcile exactly.

### T2 — Add the local dashboard trial

- create the `Transition screen` mode;
- add Generation, Baseline Revenue, Adjusted Revenue, Revenue Change, and Rating
  metric choices;
- implement driver selection, the three selected-cell calculation traces, and
  the Direct Carbon revenue-proxy disclaimer;
- implement keyboard/focus/table-alternative behavior; and
- verify Solar, Wind Template A, Wind Template B, missing SCR, and missing
  revenue states.

Gate: Divy and the team can understand what changed, why it changed, which base
was used, and which interpretation remains provisional without opening the
source workbook.

### T3 — Expand to all 9 scenarios x 6 horizons

- generalize the builder and dashboard exporter;
- emit deterministic per-asset/scenario/horizon map slices;
- add complete scenario and horizon controls;
- test structural nulls without filling them; and
- compare distribution and map behavior across all 54 combinations.

Gate: all source domains and row counts reconcile, and no scenario/horizon
selection silently falls back to another value.

### T4 — Decide production promotion

After semantic and outlier review, choose one:

```text
A. retain as rating / experimental revenue screening
B. promote validated percentage-based revenue stress
C. add OpEx and a separate Direct Carbon Cost cash-flow channel
```

Only then create an immutable three-file recipient package, publish a governed
release pointer, and enable the feature outside research status.

## Confirmed trial defaults and remaining open questions

### Owner-confirmed trial defaults

1. **Combine the two subrisk impacts additively.**
   - Use the same annual-revenue base:
     `1 + (direct_carbon_impact + market_demand_impact) / 100`.
   - Do not use sequential multiplication by default. It creates an undocumented
     interaction term between the two SCR values.

2. **Use SCR adjusted impacts operationally.**
   - Use adjusted impacts for the displayed factors and retain raw impacts beside
     them for audit.
   - They are currently identical in all non-null records, so this does not
     change current numbers but protects the contract if SCR later differentiates
     them.

3. **Lead with `$ / kWp / year` on the map.**
   - Use this unit for spatial comparison.
   - Show both `$ / kWp / year` and the illustrative `100 MW $ / year` value in
     the selected-cell detail.

4. **Start at `Expected / 2030 / Overall / Adjusted revenue`.**
   - Keep all nine scenario pathways, all six horizons, and all three drivers
     selectable.
   - Keep an explicit `research / experimental proxy` badge visible.

5. **Render missing transition values as `Unavailable`.**
   - Use a neutral map treatment and a reason code.
   - Never silently fill, convert to zero, or substitute a `1.0x` factor.

6. **Persist transition factors independently from baseline revenue.**
   - Key each factor by asset type, cell, scenario, horizon, driver, SCR source
     version, and combination method.
   - Store the calculated adjusted-revenue snapshot with the revenue release ID;
     when revenue advances beyond V6, reuse the governed factor and recalculate
   rather than re-extracting SCR.

7. **Use SCR's documented horizon semantics without changing the factors.**
   - Indicator values are 10-year averages centered on the selected horizon.
   - Financial impacts are average annual impacts from 2025 through the
     selected horizon.
   - The horizon is neither a cumulative dollar total nor a point-in-time-only
     impact. This clarification changes labels and metadata, not any impact,
     factor, or adjusted-revenue calculation.

8. **Keep a future OpEx treatment as a separate workflow.**
   - V1 may use annual revenue for the Direct Carbon proxy with its caveat.
   - When a governed OpEx layer becomes available, reuse the stored SCR Direct
     Carbon factor against OpEx and combine it with the Market Demand revenue
     channel through a separate cash-flow model.
   - Do not overwrite or silently reinterpret the V1 annual-revenue proxy.

### Questions deferred beyond the trial

9. Is SCR's exported impact scale independently confirmed to mean percentage
   points, rather than only inferred from workbook labels and behavior?
10. For a production financial model, should Direct Carbon Cost apply to revenue,
   OpEx, EBITDA, or another denominator?
11. Is the sign convention consistent across every scenario, horizon, and asset
   type?
12. Why does Wind contain two distinct economic templates, and do they correspond
    to a meaningful asset subtype or upload batch?
13. When should the accepted V6 revenue files receive a governed release pointer
    and sidecar comparable to other InfraSure deliveries?

Questions 9–13 do not block the small dashboard slice. They do block describing
the result as a production cash-flow forecast or a final governed financial
adjustment.

## Acceptance checklist

- [x] Revenue sources are SHA-pinned and identified as V6.
- [x] SCR raw and adjusted impacts remain unchanged and traceable.
- [x] Percentage conversion occurs once, only in derived trial fields.
- [x] Scope 3 and other explanatory indicators are never added as impacts.
- [x] Direct Carbon and Market Demand are shown separately against annual
      revenue, with Direct Carbon labeled as a temporary proxy.
- [x] Overall transition screening uses the documented additive same-base rule.
- [x] The calculated overall factor is not confused with SCR's A-G overall
      transition rating.
- [x] Solar 44-cell and Wind two-cell coverage differences are explicit.
- [x] Wind source regime is visible and not portrayed as geographic science.
- [x] Map metric names, legends, tooltips, selected-cell values, and exports use
      the same units and active filters.
- [x] Physical damage, transition screening, and baseline revenue remain
      separate product concepts.
- [x] The trial does not update production delivery pointers.

## Read first

- Financial interpretation:
  [`04_transition_financial_application_framework.md`](../discussions/solar_wind_physical_transition_expansion/04_transition_financial_application_framework.md)
- Current transition evidence:
  [`03_transition_sample_semantics_and_regime_findings.md`](../discussions/solar_wind_physical_transition_expansion/03_transition_sample_semantics_and_regime_findings.md)
- Existing expansion plan:
  [`SCR Solar and Wind Physical and Transition Expansion Plan.md`](SCR%20Solar%20and%20Wind%20Physical%20and%20Transition%20Expansion%20Plan.md)
- Existing physical-climate dashboard plan:
  `/Users/divy/code/work/infrasure_git_codes/Hazard_modeling/docs/plans/_cross_cutting/conus_grid/dashboard/delivery_climate_sensitivity/README.md`
- V6 revenue contract:
  `/Users/divy/code/personal/renewablesinfo/products/index_analysis_lab/docs/schema/v6_outputs_schema.md`

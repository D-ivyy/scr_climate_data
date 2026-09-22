---
author: InfraSure
created: 2026-09-22
updated: 2026-09-22
status: sample investigation complete; full-corpus extraction next
---

# SCR transition-risk sample semantics and source-regime findings

## Decision summary

The current SCR transition workbooks can be parsed into a compact, auditable
product grain, but they are **not yet safe to apply directly to InfraSure cash
flow**. Two issues must remain explicit in the next implementation:

1. SCR's embedded ReadMe labels the numeric subrisk impacts as percentages of
   asset revenue / OpEx, but its documented range conflicts with the values
   actually exported; and
2. Wind contains at least two ordered economic-content regimes even though the
   sampled files share one report date and one TICCS asset class.

```text
SCR workbook (216 rows)
        |
        +-- 9 scenarios
        +-- 6 horizons: 2025, 2030, ..., 2050
        +-- 4 indicator rows per scenario/horizon
        |
        v
deduplicate repeated impacts and ratings
        |
        v
candidate compact grain (54 rows/workbook)
cell x asset type x scenario x horizon
        |
        +-- 4 indicators + source units
        +-- 2 subrisk impacts and ratings
        +-- 1 overall transition rating
        +-- source regime + report date + provenance
```

This is a source-profiling conclusion, not approval to combine Direct Carbon
Cost and Market Demand Shifts or convert either field to dollars.

## What SCR says the impact means

The embedded ReadMe in both sampled Solar and Wind workbooks defines:

| Field | SCR definition | SCR unit |
|---|---|---|
| `subriskRevenueImpact` | Subrisk impact on asset revenue / OpEx (annualized average) | `%` |
| `adjustedSubriskRevenueImpact` | Same impact adjusted for asset-specific characteristics | `%` |

That is stronger evidence than treating the values as unitless scores.
However, the same ReadMe describes a `0-1` range while the sampled exports run
from `-0.947056` to `37.002403`, with hundreds of observations whose absolute
value exceeds 1. The safest current interpretation is therefore:

```text
raw SCR numeric impact with source-declared unit "%"
!= validated fractional multiplier
!= validated dollar cash-flow adjustment
```

InfraSure should retain the numeric value and SCR-declared unit, but mark its
financial-application status unresolved until the scale, denominator, sign,
and combination rule are confirmed.

## Current output contract differs from the embedded ReadMe

The live `Output` sheet has 20 columns and 216 rows per workbook:

```text
9 scenarios x 6 horizons x 4 indicators = 216 rows
```

The observed horizons are 2025, 2030, 2035, 2040, 2045, and 2050. The observed
scenario pathways are:

1. Below 2°C
2. Climate Breakdown
3. Climate Destabilization
4. Current Policies
5. Delayed transition
6. Expected
7. Fragmented World
8. Nationally Determined Contributions (NDCs)
9. Net Zero 2050

The embedded ReadMe instead lists six scenarios and a 2030-2060 horizon range,
and defines an `adjustedIndicatorValue` field that is absent from the current
Output sheet. Production parsing must follow the actual named Output columns
while preserving these contract discrepancies as QA findings.

## Repetition and compact grain

Within each sampled workbook:

- each subrisk impact and rating is repeated consistently across the indicator
  rows associated with its scenario and horizon;
- the overall transition rating is repeated consistently across all four
  indicator rows for a scenario and horizon; and
- raw and adjusted impacts and ratings are identical in the current sample.

Consequently, summing the repeated source rows would overcount. A normalized
raw layer may retain every source row, but the product-facing candidate should
deduplicate to one row per cell, asset type, scenario, and horizon.

## Geographic and asset-type behavior in the deterministic sample

Seven matched cells were inspected for Solar and Wind.

- Solar showed no cross-cell variation in indicators, impacts, subrisk
  ratings, or overall ratings.
- Wind varied in 30 of 216 indicator comparison groups, 30 of 108 impact
  groups, 31 of 108 subrisk-rating groups, and 31 of 54 overall-rating groups.
- Solar and Wind shared all sampled Carbon Price values but differed materially
  in Scope 1+2 and Scope 3 emissions intensity, as expected for different asset
  classes.

This evidence argues against spatial nearest-neighbor filling for transition
risk at this stage. The current outputs appear dominated by scenario, country,
and asset-template assumptions rather than local physical continuity.

## Wind has two ordered source regimes

A second deterministic test sampled 128 workbooks evenly across each source
range. Economic-output fingerprints exclude file identity and location metadata
and use the complete scenario/horizon/indicator/subrisk value content.

| Surface | Source files | Sampled | Distinct economic fingerprints | Transitions in ordered sample |
|---|---:|---:|---:|---:|
| Solar transition | 13,041 | 128 | 1 | 0 |
| Wind transition | 13,085 | 128 | 2 | 1 |

The two sampled Wind regimes are contiguous in cell/asset order:

| Sampled Wind regime | Sample count | Sampled cell range | Sampled asset-ID range | Expected / 2030 revenue growth | Expected / 2030 market-demand impact | Expected / 2025 overall rating |
|---|---:|---:|---|---:|---:|---|
| Early | 32 | 235780-267381 | `USA_17220`-`USA_20414` | 0.218766 | 0.647230 | F |
| Later | 96 | 267484-376954 | `USA_20517`-`USA_31286` | 0.630592 | 2.045696 | E |

All 128 sampled Wind files report `2026-09-16` and TICCS `IC701010`. The sample
therefore demonstrates an ordered content change, but it does not establish
whether that change was intentional, a source-model revision during batch
generation, or an upstream configuration problem.

## Implementation consequence

The full-corpus transition extraction should proceed, but it must remain a
raw/profile build rather than a recipient financial release:

```text
freeze exact inventories
        |
        v
parse named Output columns + workbook metadata
        |
        v
attach economic-content fingerprint and report date
        |
        v
locate exact Wind regime boundary and count each regime
        |
        v
profile variation and reconcile Solar's 44 missing cells
        |
        v
team/SCR interpretation decision
        |
        +-- rating-only screening package, or
        +-- validated percentage/cash-flow stress package
```

Required guardrails for the next build:

- preserve the source value exactly; do not divide by 100 in extraction;
- keep raw and adjusted fields even when they are currently equal;
- preserve source-declared unit separately from InfraSure interpretation status;
- never sum repeated impact rows;
- flag the source regime on every compact record;
- do not fill Solar's 44 absent transition cells by physical proximity without
  separate evidence; and
- do not update recipient delivery pointers or dashboard financial metrics from
  this profiling output.

The task-indexed implementation now exists under
`cloudrun/scr_transition_profile/`. Its standard-library OOXML parser was
smoke-tested against three source workbooks representing Solar, early-Wind,
and later-Wind content. All three produced 216 validated source rows, 54 compact
records, the expected report date, and the same economic fingerprint as the
independent OpenPyXL sample profiler. The next run can therefore measure the
exact full-corpus regimes without changing or financially interpreting the
source values.

## Reproducible evidence

The scripts and machine-readable results are under
[`notebooks/transition_risk/`](../../../../notebooks/transition_risk/):

- `00_sample_semantics_profile.py`
- `01_template_fingerprint_sample.py`
- `outputs/2026-09-22/transition_sample_semantics_profile.json`
- `outputs/2026-09-22/transition_compact_sample.csv`
- `outputs/2026-09-22/transition_template_fingerprint_sample.json`
- `outputs/2026-09-22/transition_template_fingerprint_sample.csv`

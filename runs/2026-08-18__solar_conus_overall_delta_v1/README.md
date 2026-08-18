# SCR Solar CONUS overall physical-damage delta V1

**Date:** 2026-08-18
**Status:** Complete; QA passed

## Purpose

This delivery provides one complete screening-level multiplier surface for the
InfraSure canonical 13,085-cell served CONUS grid. It converts SCR's overall
`adjustedTotalDamage` time series into a within-scenario change factor:

```text
factor = |future adjustedTotalDamage| / |2025 adjustedTotalDamage|
```

```text
SCR Solar workbooks (11,928 observed cells)
                     |
                     v
       overall adjustedTotalDamage by
          scenario and five-year horizon
                     |
                     v
   2025-relative raw factor on observed cells
                     |
          +----------+----------+
          |                     |
          v                     v
   observed cell          1,157 absent cells
   factor_raw             raw fields stay null
          |                     |
          |              closest observed cell
          |              by great-circle distance
          +----------+----------+
                     |
                     v
          factor_filled on all 13,085 cells
                     |
                     v
      2 scenarios x 16 horizons = 418,720 rows
```

## Files

| File | Role |
|---|---|
| `scr_solar_conus_overall_delta_v1.parquet` | Final normalized factor surface |
| `manifest.json` | Counts, hashes, source identity, imputation statistics, and acceptance checks |
| `qa_report.json` | Structural, lineage, donor-copy, baseline, and parser-equivalence checks |

## Consumer fields

| Field | Use |
|---|---|
| `factor_filled` | Complete V1 multiplier for every canonical cell |
| `factor_raw` | SCR-observed-only multiplier; null for absent workbooks |
| `percent_change_filled` | `factor_filled - 1`; e.g. `0.08` means an 8% increase |
| `is_imputed` | True only for nearest-cell-filled records |
| `source_cell_id` | Self for observed rows; donor cell for imputed rows |
| `donor_distance_km` | Great-circle distance from target cell center to source cell center |
| `baseline_damage_raw`, `future_damage_raw` | Signed SCR source values; null for absent workbooks |
| `baseline_damage_filled`, `future_damage_filled` | Signed source or donor values supporting `factor_filled` |

`iso_rto` is intentionally excluded. The file is sorted by `cell_id`,
`scenario`, and `horizon`.

## Missing-cell policy

V1 does not retry the 1,157 absent SCR requests. Each missing cell uses the
single geographically closest observed canonical grid cell, selected once and
reused for all scenario/horizon rows. Ties are resolved deterministically by
the smaller donor `cell_id`.

No averaging, spatial smoothing, ceiling, compression, or denominator floor
is applied. Extreme ratios caused by small 2025 baselines remain visible for
research and later guardrail decisions.

Across the 1,157 imputed cells, donor distance is 21.76 km at the median,
35.23 km at P95, and 86.55 km at the maximum.

## Delivery result

| Check | Result |
|---|---:|
| Canonical cells | 13,085 |
| Observed SCR cells | 11,928 |
| Nearest-cell-filled cells | 1,157 |
| Scenarios | 2 |
| Horizons | 16 (2025–2100, five-year steps) |
| Rows | 418,720 |
| Columns | 34 |
| Duplicate grain keys | 0 |
| Null `factor_filled` values | 0 |
| Cloud tasks | 128/128 succeeded |
| Artifact-tool equivalence sample | 500/500 exact matches |

Cloud execution: `scr-solar-overall-delta-v1-b4wgd`.

## Interpretation boundary

This is an internal screening surface. It is intended to scale a compatible
InfraSure physical-loss metric for scenario analysis; it is not a replacement
for hazard modeling and is not yet a client-facing or pricing-grade factor.

## Rebuild

Workbook extraction uses:

```text
notebooks/conus_solar_physical_delta/support/extract_overall_damage.mjs
```

The normalized Parquet and manifest are produced by:

```text
scripts/build_solar_overall_delta_parquet.py
```

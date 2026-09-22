---
author: InfraSure
created: 2026-09-22
updated: 2026-09-22
status: QA-passed research candidate published
---

# Onshore Wind nearest-fill implementation

## Decision

The product-facing Wind research surface uses three distinct factor layers:

```text
factor_raw
    observed SCR ratio
    null when SCR has no usable 2025 baseline

factor_filled
    factor_raw where observed
    otherwise the nearest metric-eligible Wind cell's complete factor path

factor_filled_stabilized_candidate
    factor_filled after the tested 3x/5x arctangent tail compression
```

No raw value is overwritten. Every substituted row records `is_imputed`,
`fill_method`, `source_cell_id`, `donor_distance_km`, and `quality_status`.

## Why the decision changed

The initial investigation retained 1,117 unsupported Wind cells as null. The
follow-up comparison showed that nearest-donor completion is both technically
traceable and consistent with the earlier Solar implementation:

- 1,113 of the 1,117 Wind cells overlap the older Solar missing-cell set;
- the remaining 44 older Solar missing cells are exactly the 44 workbooks still
  absent from the current Solar source;
- 1,032 Wind donors are within 30 km;
- median donor distance is 21.83 km and P95 is 35.25 km;
- maximum donor distance is 86.55 km; and
- 1,069 of 1,117 donors, or 95.70%, are in the same state.

This is strong evidence of a recurring SCR physical-damage coverage pattern,
not a Wind extraction failure. It supports a complete applied surface provided
the raw null condition and donor provenance remain visible.

## Implemented packages

| Item | Filled V1 | Stabilized V2 |
|---|---:|---:|
| Rows | 418,720 | 418,720 |
| Columns | 35 | 46 |
| Canonical cells | 13,085 | 13,085 |
| Raw factor null rows | 35,744 | 35,744 |
| Filled/applied factor null rows | 0 | 0 |
| Imputed cells | 1,117 | 1,117 |
| Compressed raw rows | n/a | 307 |
| Compressed complete-grid rows | n/a | 308 |
| Parquet SHA-256 | `1c037857055a97158ac25c2d30a6f274a2d14b410e4fd9aed134118c24dfd153` | `edee42cf4a55044367293dafab9cf1a8333c17b0fc1dbe61ff2401ed819dba09` |

Immutable research prefixes:

- `gs://infrasure-scr-data/derived/wind_overall_delta_v1_filled/run_id=20260922T122119Z/`
- `gs://infrasure-scr-data/derived/wind_overall_delta_v2_filled_candidate/run_id=20260922T122119Z/`

Remote Parquet SHA-256 values were read back from GCS and match both manifests.
Neither prefix changes a recipient `current.delivery.yml` pointer.

## QA results

All automated gates passed:

- unique `cell_id x scenario x horizon` grain;
- 13,085 canonical cells, two scenarios, and 16 horizons;
- raw source/location/value fields exactly match the immutable retain-null V1;
- V1 fields are preserved in V2 apart from the intentional schema label;
- every imputed cell has exactly 32 rows and one complete donor path;
- all donors are metric-eligible, non-imputed cells;
- raw factor nulls remain 35,744 while filled nulls are zero;
- all imputed rows use `imputed_metric_unavailable_nearest`;
- V2 identity-band, bounds, monotonicity, and source-immutability checks pass;
  and
- all 48 late-emerging raw future-damage rows are preserved across six cells.

The earlier conversational estimate of four late-emerging cells was incorrect.
The reproducible audit found six: `256041`, `283346`, `345257`, `355295`,
`355357`, and `363997`.

## Reviewed edge cases

The longest substitution is cell `327842` in California, using same-state donor
`323521` at 86.55 km. The donor path is modest: its 2100 factors are about
`1.0036x` under SSP2-4.5 and `1.0240x` under SSP5-8.5. It remains explicitly
flagged as imputed.

Only one copied donor row enters the stabilization tail: cell `284782` in Ohio,
SSP5-8.5 at 2100, copies a `4.0x` factor from cell `284781`. This raises the
complete-grid compressed count from 307 to 308 without altering the observed
distribution.

## Approval boundary and next step

This package is approved for research and controlled InfraSure integration
testing. It is not yet the governed recipient release and is not approved for
PML, VaR, TVaR, or silent presentation of imputed factors as directly observed
SCR values.

The next physical-risk step is a recipient package/dashboard staging review.
The next analytical workstream is the full Solar and Wind transition-risk
profile, beginning with unit, denominator, repetition, and spatial-variation
semantics.

## Reproducible evidence

- [`nearest_fill_validation.json`](../../../../notebooks/wind_physical_delta/outputs/2026-09-22/nearest_fill_validation.json)
- [`nearest_fill_longest_donors.csv`](../../../../notebooks/wind_physical_delta/outputs/2026-09-22/nearest_fill_longest_donors.csv)
- [`nearest_fill_late_emerging_rows.csv`](../../../../notebooks/wind_physical_delta/outputs/2026-09-22/nearest_fill_late_emerging_rows.csv)
- [`nearest_fill_imputed_compression_rows.csv`](../../../../notebooks/wind_physical_delta/outputs/2026-09-22/nearest_fill_imputed_compression_rows.csv)

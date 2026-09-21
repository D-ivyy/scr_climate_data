# SCR Solar CONUS physical-delta Parquet plan

**Date:** 2026-08-18
**Status:** V1 complete; Cloud Run build and QA passed
**Primary source:** `gs://infrasure-scr-data/physical_risks_exports/`

## Outcome

Produce one Parquet aligned to every cell in InfraSure's canonical 13,085-cell
served CONUS grid. The file will preserve observed SCR physical-damage values,
derive the overall `adjustedTotalDamage` 2025-to-future factor for both scenarios
and all five-year horizons, and make missing, invalid-baseline, guarded, and
imputed records distinguishable.

```text
11,928 observed Solar workbooks       1,157 absent workbooks
                 \                       /
                  +-- canonical 13,085-cell spine --+
                                      |
                                      v
                      normalized adjustedTotalDamage
                                      |
                       2025 baseline / future value
                                      |
                                      v
                      raw delta + QA/status/provenance
                                      |
                                      v
                    one partition-friendly Parquet file
```

## Fixed inputs

| Input | Contract |
|---|---|
| Canonical grid | `served_conus_cell_ids_v2026_06.csv`; 13,085 unique cells |
| Asset | Solar photovoltaic, TICCS `IC702010` |
| Scenarios | `ssp2-4.5`, `ssp5-8.5` |
| Horizons | 2025–2100 in five-year steps |
| Overall metric | `adjustedTotalDamage` |
| Working baseline | 2025 value in the same scenario |
| Raw source location | GCS; workbooks are not copied into Git |

## Proposed Parquet grain

One row per:

```text
cell_id x asset_type x scenario x horizon
```

The Solar delivery therefore has an expected 418,720-row canonical surface
(`13,085 × 2 × 16`). Hazard-level values may be retained in staged QA evidence,
but they are not part of the V1 final Parquet grain.

V1 was completed through Cloud Run execution
`scr-solar-overall-delta-v1-b4wgd`: 128/128 tasks succeeded, the normalized
Parquet contains 418,720 rows, and all acceptance checks passed.

## Proposed fields

| Field | Meaning |
|---|---|
| `cell_id`, `lat_idx`, `lon_idx`, `lat_center`, `lon_center` | Exact canonical grid identity |
| `state_abbr` | Optional human-readable canonical label |
| `asset_type`, `ticcs_subclass` | Solar configuration identity |
| `scenario`, `baseline_year`, `horizon` | SCR comparison axes |
| `scr_metric_name` | Fixed source field: `adjustedTotalDamage` |
| `baseline_damage_raw`, `future_damage_raw` | Signed SCR source values |
| `baseline_damage_magnitude`, `future_damage_magnitude` | Absolute loss magnitudes used in factor arithmetic |
| `absolute_change_magnitude` | Future magnitude minus baseline magnitude |
| `factor_raw` | Future magnitude divided by baseline magnitude |
| `percent_change_raw` | `factor_raw - 1` |
| `factor_applied` | Raw factor after any separately approved guardrail |
| `factor_filled` | Optional spatially completed factor; never overwrites raw |
| `factor_status` | Observed, missing source, metric unavailable, zero/near-zero baseline, imputed, or rejected |
| `imputation_method`, `donor_cell_ids`, `donor_distance_km` | Visible lineage for any fill |
| `source_uri`, `source_report_date`, `source_row_count` | Workbook provenance |
| `source_schema_hash`, `pipeline_version`, `created_at` | Reproducibility |

`factor_applied` is intentionally deferred from V1 because no cap,
compression, or other guardrail has been approved. The V1 consumer field is
`factor_filled`; `factor_raw` remains the observed-only audit field.

## Approved V1 missing-cell rule

The V1 delivery will **not retry the 1,157 absent SCR requests**. Each absent
canonical cell will use the value from its geographically closest canonical
cell with an observed SCR workbook. The same donor cell is used for all
scenario/horizon rows belonging to that missing target cell.

This is deliberately simple and deterministic. Raw and filled values remain
separate, and each imputed row records its donor cell and donor distance. No
averaging, smoothing, factor cap, or compression is applied in V1.

## Execution phases

### Phase 1 — Freeze source coverage

1. Save the bucket inventory and canonical-grid hash.
2. Record the 11,928 observed and 1,157 absent canonical cells.
3. Freeze that inventory as the V1 source surface; do not retry missing files.

Gate: exact observed and absent counts are documented.

### Phase 2 — Build the production parser

1. Stream one workbook at a time; do not hold the full 1.8 GiB corpus in memory.
2. Require the `Output` sheet and the 36-column contract.
3. Extract one distinct `adjustedTotalDamage` per asset/scenario/horizon group;
   retain hazard components only in staged QA evidence.
4. Preserve the exact source URI and report date.
5. Write a staged normalized Parquet; notebooks must not publish the final file.

Gate: every observed workbook has one parse status, and any schema drift is
quarantined rather than coerced.

### Phase 3 — Derive raw physical-damage factors

1. Join observed records to the canonical grid by exact `cell_id`.
2. Use the same-scenario 2025 denominator.
3. Store baseline, future, absolute movement, factor, and percentage change.
4. Set factors to null for missing or zero/near-zero baselines.
5. Keep Heat disruption and all combined-value fields outside the factor.

Gate: raw factor arithmetic is reproducible from stored source values.

### Phase 4 — Full-corpus QA and guardrail proposal

Run these checks by scenario, horizon, hazard, state, and region:

- file/schema/row-count consistency;
- coordinate equality and unique canonical IDs;
- raw versus adjusted differences;
- `adjustedTotalDamage` reconciliation to available hazard damage as QA;
- missing baseline and future coverage;
- factor and absolute-change distributions;
- tiny-denominator and extreme-ratio review;
- flat-factor frequency and spatial clustering.

Do not select a cap from the 17-file sample. Propose a denominator floor and any
ceiling/compression only after full distributions are available.

### Phase 5 — Complete missing cells with the approved rule

1. Keep all absent-workbook rows in the canonical surface with raw nulls.
2. Find the geographically closest observed canonical cell.
3. Copy the donor's filled damage values and factor for every matching
   scenario/horizon row.
4. Populate donor cell ID, donor distance, imputation method, and quality
   status on every filled row.
5. Confirm raw source and factor fields remain null for absent workbooks.

Structural metric blanks are not eligible for spatial filling.

### Phase 6 — Publish and validate the single Parquet

Acceptance checks:

1. Exactly 13,085 distinct canonical `cell_id` values.
2. Exactly one row per declared grain; no duplicate key.
3. Expected scenarios, horizons, and asset class only.
4. No extra/noncanonical cells.
5. Coverage-status counts reconcile to the canonical row count for every slice.
6. Observed and filled values are never conflated.
7. All factors can be reconstructed or traced to donor records.
8. A sidecar records source inventory hash, schema, code revision, QA results,
   and unresolved vendor/licensing questions.

## Team review gates

The team should approve three choices before Platform use:

1. Whether 2025 is the production baseline after SCR confirms its meaning.
2. Which InfraSure asset-level loss metric the overall SCR delta may screen;
   this does not require hazard-level delivery rows.
3. Whether a later production version needs a denominator floor, factor cap,
   compression, or a more sophisticated spatial-fill method.

Until those gates pass, the deliverable is an internal research surface—not a
client-facing EL multiplier.

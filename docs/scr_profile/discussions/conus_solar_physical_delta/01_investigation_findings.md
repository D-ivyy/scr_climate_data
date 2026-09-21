# SCR Solar CONUS investigation findings

**Investigation date:** 2026-08-18
**Source bucket:** `gs://infrasure-scr-data/physical_risks_exports/`
**Asset class:** `IC702010` — Photovoltaic Power Generation
**Status:** Evidence for execution planning; not a production release

## Bottom line

The SCR files are built on the same canonical grid identity used by InfraSure.
We do not need a spatial nearest-neighbor join to identify the returned files:
the integer `cell_id` is already the correct join key.

The source drop is incomplete, however. It contains 11,928 of the 13,085
canonical cells. The remaining 1,157 cells must first be treated as missing
source workbooks—not as zero risk and not silently filled.

```text
Canonical InfraSure served grid:  13,085 cells (100.00%)
                                  |
                                  +-- SCR workbook present: 11,928 (91.16%)
                                  |
                                  +-- workbook absent:        1,157 ( 8.84%)

Workbook IDs outside grid:             0
Duplicate workbook cell IDs:           0
Filename state mismatches:             0
```

## 1. Grid alignment

The canonical source is:

```text
Hazard_modeling/data/hazard_conus_grid/common/benchmark_grid/
served_conus_cell_ids_v2026_06.csv
```

It contains 13,085 served CONUS cells on the ERA5-native 0.25° lattice. The
canonical fields are `cell_id`, `lat_idx`, `lon_idx`, `lat_center`,
`lon_center`, and `state_abbr`; `cell_id = lat_idx * 1440 + lon_idx`.

All 11,928 parsed SCR filenames use a canonical cell ID. Embedded state and
market labels agree with the canonical grid for every returned file. A
deterministic 17-workbook sample was then opened and checked: all 17 workbook
coordinates exactly equal the canonical `lat_center` and `lon_center`.

Conclusion: use an exact `cell_id` join. Do not perform a fuzzy coordinate join.

## 2. Missing coverage is patterned

The 1,157 absent cells form 387 four-neighbor components. There are 256 isolated
missing cells, but the largest connected missing component contains 77 cells.
Missingness is especially high in several Mountain West states:

| State | Missing | Canonical cells | Missing rate |
|---|---:|---:|---:|
| Nevada | 158 | 461 | 34.27% |
| Utah | 91 | 348 | 26.15% |
| Arizona | 109 | 466 | 23.39% |
| Wyoming | 102 | 459 | 22.22% |
| New Mexico | 103 | 495 | 20.81% |
| Colorado | 80 | 461 | 17.35% |
| Montana | 109 | 691 | 15.77% |
| California | 92 | 675 | 13.63% |

That pattern is evidence against immediately copy-pasting the closest cell. A
cluster may reflect a repeatable fetch failure or another source condition. We
should re-fetch and classify the cause before deciding that interpolation is
appropriate.

## 3. Sampled workbook contract

The deterministic sample spans geographic deciles plus the smallest and largest
files. It is useful for parser/schema validation, not for estimating national
hazard coverage.

| Check | Sample result |
|---|---:|
| Workbooks opened | 17 |
| Exact coordinate matches | 17/17 |
| Schema variants | 1 |
| Rows per workbook | 986 |
| Columns per workbook | 36 |
| Output range | `A1:AJ987` |
| Scenarios | `ssp2-4.5`, `ssp5-8.5` |
| Horizons | Historical; 2025–2100 at five-year steps |
| Returned hazard families | 9 |

The nine families are Drought, Earthquake, Flood, Heat, Landslide,
Precipitation, Subsidence, Wildfire, and Wind.

All raw/adjusted value pairs were equal wherever both were populated in the 17
files. That means no adaptation adjustment is observable in this sample; it is
still a required full-corpus QA check.

## 4. Can the overall physical-damage factor be produced?

The primary test requires both a nonzero 2025 `adjustedTotalDamage` and a future
value for the same asset and scenario. Hazard-level checks explain the total but
are not proposed as final-delivery rows.

| Output | Valid 2050/2100 factor coverage in sample | Interpretation |
|---|---:|---|
| Overall `adjustedTotalDamage` | 17/17 | Primary V1 overall physical-damage factor is available in every sampled workbook. |
| Wildfire `adjustedHazardDamage` | 16/17 | Broadest hazard-specific coverage in this sample. |
| Flood `adjustedHazardDamage` | 5/17 | Usable only where both values are returned. |
| Wind `adjustedHazardDamage` | 5/17 under SSP2-4.5; 6/17 under SSP5-8.5 | Sparse and capable of unstable ratios. |
| Heat | 0/17 | SCR returns disruption, not physical damage. |
| Drought, Earthquake, Landslide, Precipitation, Subsidence | 0/17 | Indicator/rating output only in this sample. |

Across 544 sampled asset/scenario/year groups, `adjustedTotalDamage` reconciles
to the sum of populated `adjustedHazardDamage` components within `1e-12`. The
overall field is therefore a legitimate SCR physical-damage rollup in this
sample. It must still be labeled as “overall available SCR damage,” because a
blank hazard damage field is not proof of zero risk.

## 5. How the delta is derived

SCR returns the underlying signed damage outputs; InfraSure derives the factor.
For one cell, scenario, horizon, and scope:

```text
baseline magnitude = abs(adjusted damage at 2025)
future magnitude   = abs(adjusted damage at future horizon)

raw factor         = future magnitude / baseline magnitude
percentage change  = raw factor - 1
absolute movement  = future magnitude - baseline magnitude
```

For hazard scope, “adjusted damage” is `adjustedHazardDamage`. For overall
scope, it is `adjustedTotalDamage`.

Example, Solar cell `335196` in Georgia under SSP5-8.5:

```text
Overall damage
  2025 = -0.00843718
  2100 = -0.01258804
  factor = 1.49197x       (+49.20%)

Flood damage
  2025 = -0.00136798
  2100 = -0.00286825
  factor = 2.09671x       (+109.67%)

Wildfire damage
  2025 = -0.00700329
  2100 = -0.00700329
  factor = 1.00000x       (flat at returned precision)
```

The factor is dimensionless. The source values appear to be asset-value impact
fractions, but their formal unit and annualization semantics remain a vendor
confirmation item. The ratio can be studied without pretending that the source
number is an InfraSure dollar EL.

## 6. Why raw ratios need a guardrail review

The sample already contains a useful warning. Solar cell `335141` has SSP5-8.5
Wind damage of approximately `-0.00000360` in 2025 and `-0.00271475` in 2100.
The direct factor is `753.69x`, mainly because the denominator is tiny.

```text
tiny 2025 denominator + modest absolute movement = enormous ratio
```

This does not justify inventing a cap now. It justifies storing the baseline,
future value, absolute movement, and raw factor together; flagging near-zero
baselines; and selecting any floor/cap/compression only after the full
distribution and masked-cell tests are reviewed.

## Evidence files

- `notebooks/conus_solar_physical_delta/outputs/2026-08-18/bucket_grid_inventory.json`
- `notebooks/conus_solar_physical_delta/outputs/2026-08-18/missing_cell_ids.csv`
- `notebooks/conus_solar_physical_delta/outputs/2026-08-18/missing_cells_by_state.csv`
- `notebooks/conus_solar_physical_delta/outputs/2026-08-18/sample_workbook_validation.json`
- `notebooks/conus_solar_physical_delta/outputs/2026-08-18/sample_metric_availability.csv`
- `notebooks/conus_solar_physical_delta/outputs/2026-08-18/sample_delta_examples.csv`

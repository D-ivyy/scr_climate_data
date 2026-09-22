---
author: InfraSure
created: 2026-09-21
updated: 2026-09-22
status: historical retain-null candidate; completion decision superseded
---

# Onshore Wind physical-delta full-corpus findings

> **Decision update — 2026-09-22:** This document preserves the initial
> retain-null investigation. The reviewed implementation now keeps these raw
> nulls while adding a separately labeled nearest-donor `factor_filled` field.
> See
> [`02_wind_nearest_fill_implementation.md`](02_wind_nearest_fill_implementation.md)
> for the approved research candidate and QA evidence.

## Result in one view

```text
13,085 canonical cells
        |
        +-- 13,085 SCR Wind physical workbooks
        |       128/128 Cloud Run tasks succeeded
        |       0 parse errors / 0 noncanonical cells
        |
        +-- 11,968 cells with usable 2025 adjustedTotalDamage baseline
        |       382,976 raw factor rows
        |       raw range: 0.03× to 380×
        |       ordinary body: median 1.00×, P95 1.20×, P99 1.56×
        |
        +-- 1,117 cells without a usable 2025 damage baseline
                35,744 factor rows remain null
                no nearest-neighbor substitution
                late-emerging raw damage is retained where present
```

The full file inventory is complete, but the overall physical-damage metric is
not available at every location. File coverage and metric coverage are therefore
different concepts and must not be reported as the same percentage.

## Execution evidence

| Item | Result |
|---|---:|
| Source workbooks | 13,085 |
| Canonical cells | 13,085 |
| Cloud Run execution | `scr-wind-overall-delta-v1-h9vwm` |
| Cloud tasks | 128/128 succeeded |
| Parse errors | 0 |
| Workbook rows | 986 in every workbook |
| Workbook header schemas | 1 |
| Usable factor cells | 11,968 |
| Metric-unavailable cells | 1,117 |
| Missing source workbooks | 0 |

The execution used immutable run ID `20260921T171946Z`, parser SHA-256
`1c9e4fdc7b3f5300da755c0ed1cd3dcda3151cb35960c9cc80bf8c1b2f7b3ed9`,
and inventory SHA-256
`fadf7a87179cf73b73847e1806d04ee104512c9e86366152441e466b97f7827e`.

## What the 1,117 unsupported cells mean

The same 1,117 cells lack a 2025 `adjustedTotalDamage` baseline in both SSP
scenarios. This is not a failed download or parser error.

Direct workbook inspection found two cases:

1. **No physical-damage output:** many workbooks have no hazard or total damage
   values at any horizon, while Heat disruption remains populated. Because this
   workstream intentionally uses physical damage—not disruption—there is no
   damage factor to calculate.
2. **Late-emerging damage with blank baseline:** three cells under SSP2-4.5 and
   five under SSP5-8.5 have a blank 2025 damage baseline and very small nonzero
   Wind damage only at later horizons. A multiplicative factor is undefined
   because the denominator is absent/zero-like.

```text
2025 damage blank + future damage blank
        -> no physical-damage change signal -> factor stays null

2025 damage blank + future damage appears
        -> emerging-damage case -> raw future retained, factor stays null
```

Setting either case to `1×` would falsely label an unsupported factor as a
measured neutral change. Nearest-neighbor filling would also replace a real
metric condition with another cell's ratio. Both options are rejected for the
current Wind candidate.

## Raw factor distribution

Across the 382,976 valid factor rows:

| Statistic | Raw factor |
|---|---:|
| Minimum | 0.0300× |
| P01 | 0.9629× |
| P05 | 1.0000× |
| Median | 1.0000× |
| P95 | 1.2000× |
| P99 | 1.5621× |
| Maximum | 380.0000× |

Only a small tail is extreme:

- 23 rows are below `1/3×`;
- 286 rows are above `3×`; and
- 173 rows are above `5×`.

The tail is driven by very small SCR baselines. Both scenarios have a minimum
nonblank 2025 magnitude of `1e-10`; approximately 840 cells per scenario are
below `1e-6`. The maximum 380× factor, for example, is produced by a movement
from `1e-6` to `0.00038`, not by a 380-fold large absolute loss amount.

## Stabilization experiment

The same 15-method experiment used for Solar was rerun on the valid Wind factor
rows. It did not fill the 1,117 unsupported cells.

| Method | Rows changed | Share of valid rows | Range | Temporal/scenario reversals |
|---|---:|---:|---:|---:|
| Raw | 0 | 0% | 0.03×–380× | 0 |
| Hard 5× cap | 182 | 0.0475% | 0.20×–5× | 0, but creates ties |
| `1e-4` denominator floor | 28,937 | 7.56% | 0.534×–27.32× | 2 scenario reversals |
| Spatial 3×3 ratio | 176,726 | 46.15% | 0.40×–97× | thousands |
| Spatial outlier replacement | 169 | 0.0441% | 0.20×–9.33× | 95 total reversals |
| **Arctangent soft log, 3×/5×** | **307** | **0.0802%** | **0.2089×–4.8921×** | **0** |

The arctangent method again gives the cleanest numerical behavior:

- the `1/3×–3×` identity band is exactly unchanged;
- only the extreme tail moves;
- materially distinct factor values retain strict ordering;
- no temporal or scenario reversals or ties are introduced; and
- null factors remain null.

Machine-precision duplicates such as `5.0` and `5.000000000000001` are treated
as the same raw value for monotonicity QA. Materially distinct inputs must still
map to strictly ordered outputs.

## Candidate artifacts

Two immutable research artifacts were produced from the same full-corpus
source and published under SCR's `derived/` research area:

| Artifact | Rows | Columns | SHA-256 |
|---|---:|---:|---|
| Raw V1 research Parquet | 418,720 | 35 | `8bc750c9c841a2ee47f8a9cccfdae78e14f961a2a435d7f957687e97321a60da` |
| Stabilized V2 candidate | 418,720 | 47 | `0b86a50b2f66fdbee9c497a999c96412e0391ff9444e604e002335d65e137c71` |

The V2 QA passed row parity, source-column preservation, null-pattern
preservation, identity-band equality, symmetric bounds, strict monotonicity,
and source immutability checks. The candidate changes 307 rows and preserves
35,744 null factor rows.

GCS packages:

- `gs://infrasure-scr-data/derived/wind_overall_delta_v1_raw/run_id=20260921T171946Z/`
- `gs://infrasure-scr-data/derived/wind_overall_delta_v2_candidate/run_id=20260921T171946Z/`

Each package contains a Parquet, manifest, README, and QA report. The remote
Parquet SHA-256 values match the documented local hashes. These prefixes are
research artifacts; neither has been promoted into the recipient delivery or
`current.delivery.yml`.

## Recommendation

Carry the Wind V2 artifact forward as a **research / integration candidate**:

```text
usable 2025 baseline
    -> raw factor
    -> arctangent 3×/5× stabilized candidate

no damage baseline
    -> factor remains null
    -> explicit metric_unavailable status
    -> raw future damage retained if it later appears
```

Do not publish it as a complete product multiplier yet. The next review gate is
to confirm that the product accepts an unavailable factor for 1,117 cells and
displays that state explicitly. No PML, VaR, or TVaR scaling is permitted.

## Reproducible evidence

- [`notebooks/wind_physical_delta/`](../../../../notebooks/wind_physical_delta/)
- [`full_extraction_profile.json`](../../../../notebooks/wind_physical_delta/outputs/2026-09-21/full_extraction_profile.json)
- [`factor_distribution_by_horizon.csv`](../../../../notebooks/wind_physical_delta/outputs/2026-09-21/factor_distribution_by_horizon.csv)
- [`metric_unavailable_cells.csv`](../../../../notebooks/wind_physical_delta/outputs/2026-09-21/metric_unavailable_cells.csv)
- [`factor_stabilization_experiment.json`](../../../../notebooks/wind_physical_delta/outputs/2026-09-21/factor_stabilization/factor_stabilization_experiment.json)

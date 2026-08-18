# Notes — SCR Solar Overall-Factor Stabilization V2

## Evidence snapshot

- Repository: `/Users/divy/code/personal/renewablesinfo/scr_climate_data`
- Branch/commit: `agent/scr-dashboard-multi-asset-interactions` at `60f408749ebb896a2ec1377f8861876801f0e8d8`; three commits ahead of upstream.
- Working tree: dirty. Task-scoped V2 builder, experiment, reports, run package, and history are uncommitted; unrelated/pre-existing dashboard, ZIP, profile, example, and scope changes were preserved.
- External release: V2 GCS research delivery published and verified.
- Platform release: not implemented; no database, service, or client application changed.
- Evidence reconciliation: 2026-08-18 15:35 EDT.

## Implementation and investigation log

1. Reconfirmed the Solar V1 raw maximum of `1,556.745114921×` and its raw
   factor definition.
2. Inspected 20 targeted high-outlier SCR workbooks. Both hazard-support changes
   and like-for-like extreme hazards were present; SSP5 like-for-like Wind
   reached `201.850×` in the inspected sample.
3. Reconstructed all 11,928 observed total-damage records from the successful
   Cloud Run result shards and joined them to the canonical grid for spatial
   testing.
4. Implemented a reproducible 15-method experiment covering raw, hard cap,
   power, symmetric plain log, denominator floor, multiple soft-log settings,
   arctangent soft log, full spatial ratio, and targeted spatial replacement.
5. Evaluated core distortion, tail percentiles, changed shares, spatial
   roughness, temporal reversals/ties, scenario reversals/ties, and synthetic
   EAL/TIV stress outcomes.
6. The leading pre-build candidate was a 3×/5× `tanh` soft ceiling. The first V2
   build stopped at QA before publication because identity-band bit equality and
   strict global monotonicity checks failed; the key substantive issue was
   float64 saturation near the asymptote.
7. Added and reran the arctangent version. It preserved the exact identity band,
   retained strict ordering, and reached `4.9162×` at the raw maximum while
   remaining below the 5× asymptote.
8. Built V2 from the immutable V1 Parquet. V2 contains 418,720 rows and 46
   columns; all non-schema V1 fields match exactly.
9. Uploaded Parquet, QA report, README, then manifest to the immutable V2 GCS
   prefix with generation-zero write preconditions.
10. Re-downloaded all four GCS objects. Parquet, QA, and README hashes matched
    the published manifest.

## Commands and verification

Working directory:

```text
/Users/divy/code/personal/renewablesinfo/scr_climate_data
```

Run the comparative experiment:

```bash
python3 notebooks/conus_solar_physical_delta/03_factor_stabilization_experiment.py \
  --shards /path/to/cloud/result/shards \
  --grid /Users/divy/code/work/infrasure_git_codes/Hazard_modeling/data/hazard_conus_grid/common/benchmark_grid/served_conus_cell_ids_v2026_06.csv \
  --output-dir notebooks/conus_solar_physical_delta/outputs/2026-08-18/factor_stabilization
```

Build V2:

```bash
/Users/divy/code/work/infrasure_git_codes/Hazard_modeling/.venv/bin/python \
  scripts/build_solar_overall_delta_v2.py \
  --source-parquet runs/2026-08-18__solar_conus_overall_delta_v1/scr_solar_conus_overall_delta_v1.parquet \
  --source-manifest runs/2026-08-18__solar_conus_overall_delta_v1/manifest.json \
  --output-dir runs/2026-08-18__solar_conus_overall_delta_v2 \
  --run-id 20260818T193139Z
```

Observed result:

```text
status=passed
rows=418720
columns=46
raw_changed=624
filled_changed=626
output_sha256=864c1aa2f796fdcf04bc4d4c012ec9793dd356445d1fdb8d59ccde44a301af1e
```

Read-only GCS verification:

```bash
gcloud storage ls -l \
  'gs://infrasure-scr-data/derived/solar_overall_delta_v2/run_id=20260818T193139Z/*'
```

Expected: four objects totaling 31,567,652 bytes.

## Metrics

| Item | Before | V2/current | Evidence |
| --- | ---: | ---: | --- |
| Rows | 418,720 | 418,720 | V1/V2 Parquet parity |
| Columns | 34 | 46 | V2 QA report |
| Canonical cells | 13,085 | 13,085 | manifest |
| Observed cells | 11,928 | 11,928 | manifest |
| Raw factor range | 0.03947×–1,556.745× | retained | V1/V2 columns |
| Candidate factor range in data | none | 0.210084×–4.916205× | V2 QA |
| Raw rows compressed | none | 624 | V2 QA |
| Filled rows compressed | none | 626 | V2 QA |
| Filled candidate nulls | n/a | 0 | V2 QA |
| Duplicate keys | 0 | 0 | explicit readback check |
| Non-schema V1 parity failures | n/a | 0 | explicit column comparison |
| Remote objects | none | 4 | GCS listing |

## Failures and recovery

- **Rejected solution:** hazard-level factors alone. Like-for-like Wind still
  reached `201.85×`; hazard granularity is diagnostic, not a complete fix.
- **Rejected solution:** denominator floor. It materially changed ordinary
  values and did not control the tail.
- **Rejected solution:** spatial replacement as an applied rule. It introduced
  time/scenario reversals.
- **Stopped V2 attempt:** `tanh` soft ceiling failed the strict QA gate before
  publication. Recovery was to test an arctangent saturation curve, rerun the
  complete experiment, and rebuild from unchanged V1.

## External state

- GCP project: `modeling-nonprod-svc-db5x`.
- Source V1: `gs://infrasure-scr-data/derived/solar_overall_delta_v1/run_id=20260818T160023Z/`.
- Published V2: `gs://infrasure-scr-data/derived/solar_overall_delta_v2/run_id=20260818T193139Z/`.
- V2 Parquet SHA-256: `864c1aa2f796fdcf04bc4d4c012ec9793dd356445d1fdb8d59ccde44a301af1e`.
- V2 QA SHA-256: `88d8b471c5d2afd3004e09e8843e80f63debd5764ee20bf84a12ad6e984c9eec`.
- V2 README SHA-256: `d400286bd7ca3ce53e492a724d6477df8f21e167fd7a1fdd8e2ceec3fbd3ade9`.
- Last verified: 2026-08-18 approximately 15:34 EDT through remote re-download.

## Key insights

1. A bounded transform must be tested in its actual storage precision; a sound
   symbolic formula can still lose distinctions near an asymptote.
2. The cleanest method is piecewise: preserve the ordinary range exactly and
   transform only the extreme tail.
3. Numerical stabilization and financial calibration are separate approval
   gates. Passing the first does not prove the second.
4. Raw factors, candidate factors, parameters, and compression flags should be
   delivered together so that the adjustment is fully auditable.

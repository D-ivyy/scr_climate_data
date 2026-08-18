# Notes — SCR Solar CONUS Overall Physical-Damage Delta V1

## Evidence snapshot

- Repository: `/Users/divy/code/personal/renewablesinfo/scr_climate_data`
- Branch/HEAD: `agent/scr-dashboard-multi-asset-interactions` at `60f408749ebb896a2ec1377f8861876801f0e8d8`
- Upstream: `origin/agent/scr-dashboard-multi-asset-interactions`; local branch is three commits ahead.
- Working tree: dirty. Task-scoped scope/discussion/plan/notebook/cloud/build/run/history files are uncommitted; dashboard, ZIP, profile, output-example, and other existing changes were not cleaned or attributed to this task.
- Release state: final data package is published externally to GCS and verified; repository implementation/documentation is not committed or pushed.
- Evidence reconciliation: 2026-08-18 14:25 EDT.

## Implementation and investigation log

1. **Canonical-grid reconciliation.** Confirmed the Hazard_modeling served-CONUS file contains 13,085 unique 0.25° canonical cells. SCR provided 11,928 Solar workbooks; all workbook IDs were canonical and unique, leaving 1,157 absent cells.

2. **Workbook/schema investigation.** Deterministic geographic and size-based samples showed one 36-column `Output` schema, 986 data rows per workbook, two scenarios, `Historical` plus 2025–2100 five-year horizons, and nine hazard groups. `adjustedTotalDamage` was available consistently for all observed workbooks and production horizons.

3. **Full distribution analysis.** Parsed the complete observed corpus during investigation and measured horizon/scenario factor distributions, tiny-baseline sensitivity, outliers, and maps. This supported use of the overall factor but did not justify a cap.

4. **Missing-cell decision.** The owner rejected another retry cycle and approved single closest-observed-cell completion. Great-circle donor distances were 21.76 km median, 35.23 km P95, and 86.55 km maximum.

5. **Local production attempt.** A ten-shard artifact-tool run was started. After the owner raised local-load concerns, it was stopped cleanly. The resumable extractor had saved exactly 500 records, 50 per shard.

6. **Cloud parser equivalence.** Implemented a fixed OOXML parser using Python's standard library for the standard Cloud SDK runtime. Compared it against all 500 saved artifact-tool records. All 500 matched exactly across cell ID, status, row count, headers, and totals.

7. **First Cloud Run failure.** Execution `scr-solar-overall-delta-v1-xvrns` was cancelled after the first 32 tasks failed immediately. Decisive error:

   ```text
   Permission 'storage.objects.get' denied ...
   project-service-account@modeling-nonprod-svc-db5x.iam.gserviceaccount.com
   ... infrasure-scr-data/.../run_task.py
   ```

   Recovery: stage the frozen code, inventory, and workbooks under a run-specific `infrasure-benchmark` prefix accessible to the established runtime service account.

8. **First smoke failure.** One-file execution `scr-solar-overall-delta-v1-wwr28` reached and SHA-verified the script but failed because the image has no `python` command. Decisive error: `/bin/bash: python: command not found`.

9. **Successful smoke.** Changed the command to `python3`. Execution `scr-solar-overall-delta-v1-rbjqm` completed, uploaded one result, and matched the corresponding artifact-tool record exactly.

10. **Successful full fanout.** Execution `scr-solar-overall-delta-v1-b4wgd` completed 128/128 tasks with parallelism 32 in 5m15.52s. All 11,928 source workbooks were present in the result shards and none had parse errors.

11. **Parquet build and QA.** Joined results to the canonical grid; selected one donor per absent cell; wrote 418,720 rows; ran structural, factor, status, donor, baseline, and cross-parser checks. All checks passed.

12. **Publication and verification.** Uploaded Parquet, QA report, README, then manifest to the immutable SCR derived prefix. Re-downloaded the Parquet; local and remote SHA-256 both equaled `1f087bf8...`.

13. **Cleanup and hardening.** Deleted temporary local workbook/result caches, freeing roughly 1.8 GiB. Updated the current Cloud task parser to protect outputs with `--if-generation-match=0`. The raw runtime staging copy was deliberately retained.

## Reproduction and verification commands

Working directory for commands below:

```text
/Users/divy/code/personal/renewablesinfo/scr_climate_data
```

Inspect the successful external execution:

```bash
gcloud run jobs executions describe scr-solar-overall-delta-v1-b4wgd \
  --region=us-central1 \
  --format='yaml(metadata.name,status.completionTime,status.succeededCount,status.failedCount,status.conditions)'
```

Expected decisive result:

```text
Completed=True
succeededCount=128
completionTime=2026-08-18T16:15:52.414059Z
```

Inspect published artifacts:

```bash
gcloud storage ls -l \
  'gs://infrasure-scr-data/derived/solar_overall_delta_v1/run_id=20260818T160023Z/*'
```

Expected: exactly four objects totaling 23,066,865 bytes.

Verify the local Parquet checksum:

```bash
shasum -a 256 \
  runs/2026-08-18__solar_conus_overall_delta_v1/scr_solar_conus_overall_delta_v1.parquet
```

Expected:

```text
1f087bf8a7959a8ae5c33c7b27a064e22433791fc57011aa24c4a2deaef5c482
```

Inspect final table dimensions with the established Hazard Python environment:

```bash
/Users/divy/code/work/infrasure_git_codes/Hazard_modeling/.venv/bin/python - <<'PY'
import pyarrow.parquet as pq
p = 'runs/2026-08-18__solar_conus_overall_delta_v1/scr_solar_conus_overall_delta_v1.parquet'
t = pq.read_table(p, columns=['cell_id', 'scenario', 'horizon', 'factor_filled'])
print(t.num_rows, t.num_columns, t.column('factor_filled').null_count)
print(len(set(t.column('cell_id').to_pylist())))
PY
```

Expected:

```text
418720 4 0
13085
```

The production normalization command was:

```bash
/Users/divy/code/work/infrasure_git_codes/Hazard_modeling/.venv/bin/python \
  scripts/build_solar_overall_delta_parquet.py \
  --grid /Users/divy/code/work/infrasure_git_codes/Hazard_modeling/data/hazard_conus_grid/common/benchmark_grid/served_conus_cell_ids_v2026_06.csv \
  --shards /tmp/scr_cloud_results_20260818T160023Z \
  --output runs/2026-08-18__solar_conus_overall_delta_v1/scr_solar_conus_overall_delta_v1.parquet \
  --manifest runs/2026-08-18__solar_conus_overall_delta_v1/manifest.json
```

The referenced temporary shard directory was deleted after verified publication. Rebuilding requires a new run-specific extraction/reconciliation directory; do not assume the command is immediately rerunnable as written.

## Metrics

| Item | Before | Final | Evidence |
| --- | ---: | ---: | --- |
| Canonical cells | 13,085 | 13,085 | grid + QA |
| Observed SCR cells | 11,928 | 11,928 | source inventory + QA |
| Missing cells | 1,157 | 0 null filled cells | nearest-cell completion + QA |
| Imputed rows | 0 | 37,024 | QA report |
| Scenarios | 2 | 2 | manifest + QA |
| Horizons | 16 production horizons | 16 | manifest + QA |
| Final rows | none | 418,720 | Parquet + QA |
| Duplicate keys | unknown | 0 | QA report |
| Null `factor_filled` | not built | 0 | QA report |
| Cloud tasks | not run | 128/128 succeeded | execution `b4wgd` |
| Parser equivalence | not tested | 500/500 exact | QA report |
| Parquet size | none | 23,058,501 bytes | local + remote object |
| Local temporary source cache | 1.8 GiB | removed | post-publication cleanup |

## External state

- GCP project: `modeling-nonprod-svc-db5x`.
- Region: `us-central1`.
- Cloud Run job: `scr-solar-overall-delta-v1`.
- Completed production extraction: `scr-solar-overall-delta-v1-b4wgd`.
- Job's current parser object: `run_task_v2.py`, SHA-256 `1c9e4fdc7b3f5300da755c0ed1cd3dcda3151cb35960c9cc80bf8c1b2f7b3ed9`.
- Actual successful execution parser SHA-256: `424a2e8603036eaac66d8e1edf1d7393cc5395e18b6243fa2706d91463f96f37`.
- Frozen full inventory SHA-256: `69ed4057ef05219b1c062ca64eacde58db9d57c701b2df9801e4e2852eae778a`.
- Original source: `gs://infrasure-scr-data/physical_risks_exports/`.
- Runtime staging: `gs://infrasure-benchmark/scr_climate_data/dev/cloudrun/solar_overall_delta_v1/run_id=20260818T160023Z/`.
- Final publication: `gs://infrasure-scr-data/derived/solar_overall_delta_v1/run_id=20260818T160023Z/`.
- No Platform database, service, or client-facing application was changed.

## Key insights

1. The overall SCR metric is much more complete and operationally useful for this screening purpose than a forced hazard-by-hazard production surface.
2. Keeping `factor_raw` separate from `factor_filled` prevents imputation from becoming invisible.
3. A single donor per target cell preserves scenario/time coherence better than independently selecting donors per row.
4. A 500-record equivalence gate plus a one-file runtime smoke prevented parser/runtime uncertainty from contaminating the full cloud run.
5. Cloud execution was substantially faster, but IAM/storage boundaries must be designed explicitly rather than assumed from another Hazard job.
6. Extreme ratios require absolute-value context; they should not automatically dictate a cap.

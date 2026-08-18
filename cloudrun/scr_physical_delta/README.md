# SCR physical-delta Cloud Run extraction

This folder owns the task-indexed workbook extraction used by the Solar V1
delivery. `run_task.py` reads a SHA-pinned JSON source inventory, assigns files
by `CLOUD_RUN_TASK_INDEX / CLOUD_RUN_TASK_COUNT`, extracts the fixed SCR
`adjustedTotalDamage` contract, and writes one JSON result per task.

## Solar V1 proof

```text
11,928 XLSX workbooks
        |
        v
128 Cloud Run tasks (parallelism 32)
        |
        v
128 result shards / 0 failed tasks
        |
        v
scripts/build_solar_overall_delta_parquet.py
        |
        v
418,720-row canonical Parquet
```

The production parser was compared against 500 workbook results extracted by
`@oai/artifact-tool`; all 500 matched exactly. Full execution:
`scr-solar-overall-delta-v1-b4wgd`.

Task result uploads use an object-generation-zero precondition. Re-executing a
job against an existing output prefix fails instead of overwriting evidence.

## Runtime storage boundary

The existing Hazard Cloud Run service account cannot read
`gs://infrasure-scr-data`. For V1, the frozen inputs were staged without
modification under:

```text
gs://infrasure-benchmark/scr_climate_data/dev/cloudrun/
  solar_overall_delta_v1/run_id=20260818T160023Z/
```

The original SCR bucket remains the source of truth. Before repeating this for
another asset class, either grant the job service account read access to the
SCR bucket or deliberately create a new run-specific staging prefix. Never
silently treat the staging copy as the authoritative source.

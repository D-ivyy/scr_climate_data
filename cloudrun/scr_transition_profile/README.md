# SCR transition-risk Cloud Run extraction

This folder owns the task-indexed parser for the transition-risk profiling run.
It reads the current 20-column SCR `Output` sheet, validates the observed
216-row contract, and emits 54 compact scenario/horizon records per workbook.

The parser deliberately does **not**:

- divide impact values by 100;
- convert impacts to dollars or cash flow;
- combine Direct Carbon Cost with Market Demand Shifts;
- fill missing cells; or
- publish recipient delivery metadata.

Each workbook result retains its source URI, raw and adjusted impacts/ratings,
report date, schema hash, and an economic-content fingerprint. The fingerprint
is required because deterministic sampling found one Solar template and two
ordered Wind templates.

`summarize_shards.py` streams completed result shards into a small full-corpus
QA artifact. It verifies task/file/cell counts, parses, compact grain, domains,
impact distributions, and exact economic-fingerprint segments without loading
the roughly 900 MiB asset result set into memory.

Local validation:

```bash
python3 cloudrun/scr_transition_profile/run_task.py \
  --local-input-dir /path/to/sample_xlsx \
  --output /tmp/transition_sample_results.json
```

The Cloud Run environment contract matches the physical extractor:

- `SCR_INVENTORY_URI`
- `SCR_INVENTORY_SHA256`
- `SCR_OUTPUT_ROOT`
- `CLOUD_RUN_TASK_INDEX`
- `CLOUD_RUN_TASK_COUNT`

The source inventory must be immutable and run-specific. A full run is a
profiling artifact until unit/denominator semantics and the Wind source-regime
change are resolved.

`prepare_run.py` freezes the exact source URI list and can stage the workbooks
under a run-specific immutable prefix when the Cloud Run service account cannot
read `gs://infrasure-scr-data` directly.

# Handoff — SCR Solar Overall-Factor Stabilization V2

## 60-second state summary

1. Solar V1 remains immutable and retains the raw maximum factor of `1,556.745×`.
2. Fifteen transformation/parameter variants were tested across 11,928 observed cells, two scenarios, and sixteen horizons.
3. Hazard-level calculation alone was rejected as the solution; like-for-like Wind reached `201.85×` in the targeted outlier sample.
4. The selected numerical candidate is `symmetric_piecewise_soft_log_arctan`, unchanged from `0.333333×` through `3×`, with 5×/0.20× asymptotes.
5. A first `tanh` build was stopped by QA before publication because extreme finite inputs could lose numerical distinction near the asymptote.
6. V2 passed local QA with 418,720 rows, 46 columns, zero duplicate keys, zero filled-candidate nulls, exact V1 non-schema parity, and strict factor ordering.
7. Only 624 observed raw rows and 626 complete-grid rows are compressed.
8. V2 is published and checksum-verified at `gs://infrasure-scr-data/derived/solar_overall_delta_v2/run_id=20260818T193139Z/`.
9. This is a GCS research delivery and numerical screening candidate, not an approved Platform/client financial release.
10. The next safe step is representative Solar EAL/TIV calibration; do not modify or republish V2 first.

## Exact starting state

- Repository: `/Users/divy/code/personal/renewablesinfo/scr_climate_data`
- Branch: `agent/scr-dashboard-multi-asset-interactions`
- HEAD: `60f408749ebb896a2ec1377f8861876801f0e8d8`
- Upstream: `origin/agent/scr-dashboard-multi-asset-interactions`; local branch is three commits ahead.
- PR/commit: none created for this task.
- Working tree: mixed and dirty. V2 task files are uncommitted alongside unrelated/pre-existing changes; do not broadly stage, clean, or discard.
- Data release: V2 GCS research artifact published and verified.
- Platform production release: not implemented; the published GCS package is a
  research delivery only.

## Read first

1. `runs/2026-08-18__solar_conus_overall_delta_v2/README.md` — consumer contract and release boundary.
2. `runs/2026-08-18__solar_conus_overall_delta_v2/manifest.json` — immutable source, parameters, hashes, and approval status.
3. `runs/2026-08-18__solar_conus_overall_delta_v2/qa_report.json` — acceptance checks, counts, range, and columns.
4. `docs/scr_profile/discussions/conus_solar_physical_delta/04_factor_stabilization_experiment.md` — method comparison and the `tanh`-to-`arctan` refinement.
5. `notebooks/conus_solar_physical_delta/03_factor_stabilization_experiment.py` — reproducible comparative study.
6. `scripts/build_solar_overall_delta_v2.py` — exact V1-to-V2 transformation and release builder.
7. `runs/2026-08-18__solar_conus_overall_delta_v1/README.md` — immutable raw/fill source contract.

## Safe next action

1. Select 6–10 representative InfraSure Solar assets spanning low, typical,
   and high baseline EAL/TIV rates and, where possible, locations whose V2 rows
   were compressed.
2. Join each asset to `cell_id`, scenario, and horizon in V2.
3. Calculate side by side:

   ```text
   raw future EAL        = current EAL × factor_filled
   candidate future EAL  = current EAL × factor_filled_stabilized_candidate
   raw/candidate EAL rate = future EAL / TIV
   ```

4. Review every compressed result and stop before Platform implementation if
   the team has not approved the 3× start, 5× ceiling, reciprocal lower bound,
   and target financial field.
5. After Solar approval, repeat the distribution experiment for Wind and Gas
   before deciding whether parameters are universal.

## Verification / repro

From the repository root, inspect the published package:

```bash
gcloud storage ls -l \
  'gs://infrasure-scr-data/derived/solar_overall_delta_v2/run_id=20260818T193139Z/*'
```

Expected: exactly four objects totaling 31,567,652 bytes.

Verify the local Parquet and QA:

```bash
/Users/divy/code/work/infrasure_git_codes/Hazard_modeling/.venv/bin/python - <<'PY'
import hashlib, json
from pathlib import Path
import pyarrow.parquet as pq

root = Path('runs/2026-08-18__solar_conus_overall_delta_v2')
manifest = json.loads((root / 'manifest.json').read_text())
qa = json.loads((root / 'qa_report.json').read_text())
table = pq.read_table(root / manifest['output_file'], columns=[
    'cell_id', 'scenario', 'horizon', 'factor_filled',
    'factor_filled_stabilized_candidate'
])
h = hashlib.sha256((root / manifest['output_file']).read_bytes()).hexdigest()
keys = set(zip(table['cell_id'].to_pylist(), table['scenario'].to_pylist(), table['horizon'].to_pylist()))
print(qa['status'], table.num_rows, len(keys), table['factor_filled_stabilized_candidate'].null_count)
print(h)
PY
```

Expected:

```text
passed 418720 418720 0
864c1aa2f796fdcf04bc4d4c012ec9793dd356445d1fdb8d59ccde44a301af1e
```

## Files and artifacts

- `runs/2026-08-18__solar_conus_overall_delta_v2/scr_solar_conus_overall_delta_v2.parquet` — generated, local, untracked 31,560,362-byte data artifact.
- `runs/2026-08-18__solar_conus_overall_delta_v2/manifest.json` — generated, local, untracked release manifest.
- `runs/2026-08-18__solar_conus_overall_delta_v2/qa_report.json` — generated, local, untracked QA evidence.
- `runs/2026-08-18__solar_conus_overall_delta_v2/README.md` — generated, local, untracked consumer documentation.
- `notebooks/conus_solar_physical_delta/03_factor_stabilization_experiment.py` — local, untracked investigation code.
- `notebooks/conus_solar_physical_delta/outputs/2026-08-18/factor_stabilization/` — local, generated experiment outputs.
- `docs/scr_profile/discussions/conus_solar_physical_delta/04_factor_stabilization_experiment.md` — local, untracked living analysis.
- `scripts/build_solar_overall_delta_v2.py` — local, untracked V2 builder.
- `gs://infrasure-scr-data/derived/solar_overall_delta_v2/run_id=20260818T193139Z/` — externally published and verified GCS research package.

## Guardrails / do not

- Do not overwrite V1 or V2 objects; use a new schema/run prefix for changes.
- Do not present `factor_filled_stabilized_candidate` as scientifically proven
  or client-approved.
- Do not use the candidate for PML or TVaR.
- Do not remove raw factor, imputation, source, or donor-lineage fields.
- Do not silently replace factors with spatial or hazard-level estimates.
- Do not assume Solar parameters apply to Wind or Gas.
- Do not broadly stage, commit, clean, or push the mixed working tree.
- Do not place credentials or sensitive connection material in documentation.

## Open risks and decisions

- Which exact InfraSure EAL/cash-flow field should consume the candidate?
- Does representative asset testing support 3×/5×, or should the parameters be
  asset-class-specific?
- Is the reciprocal 0.20× lower asymptote acceptable, or should decreases be
  handled more conservatively?
- Should V2 remain a GCS-only data artifact or be referenced through a governed
  Platform ingestion table/view?
- Do Wind and Gas exhibit the same tail shape and denominator instability?

## Requested outcome from the next model

Produce an asset-level Solar calibration report using representative InfraSure
EAL/TIV records. Show raw versus stabilized future EAL and EAL/TIV by scenario
and horizon, identify every ceiling-affected result, and recommend whether to
approve, revise, or reject the 3×/5× parameters. Do not alter or republish V2
until that review is complete.

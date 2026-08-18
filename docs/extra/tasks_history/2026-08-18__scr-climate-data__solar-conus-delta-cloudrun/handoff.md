# Handoff — SCR Solar CONUS Overall Physical-Damage Delta V1

## 60-second state summary

1. Solar V1 is complete: one 418,720-row Parquet covers all 13,085 canonical cells, two SCR scenarios, and sixteen 2025–2100 horizons.
2. The factor is `abs(future adjustedTotalDamage) / abs(2025 adjustedTotalDamage)` within each scenario.
3. SCR directly observed 11,928 cells; 1,157 missing cells use one geographically closest observed donor across every scenario/horizon.
4. Raw and imputed values are not conflated: use `factor_raw` for observed-only analysis and `factor_filled` for the complete surface.
5. Cloud Run execution `scr-solar-overall-delta-v1-b4wgd` completed 128/128 tasks in 5m15.52s.
6. QA passed all structural, baseline, lineage, donor-copy, and parser-equivalence checks; 500/500 artifact-tool records matched exactly.
7. The complete four-object delivery is published under `gs://infrasure-scr-data/derived/solar_overall_delta_v1/run_id=20260818T160023Z/` and the Parquet hash was verified after remote re-download.
8. No ceiling, compression, or denominator floor is applied; the maximum factor is 1556.745 because tiny 2025 denominators remain visible.
9. The Cloud Run runtime needed a 1.8 GiB run-specific staging copy in `infrasure-benchmark`; that copy remains and is not source truth.
10. Implementation/docs/data artifacts are uncommitted in a mixed dirty worktree; do not broadly stage, clean, commit, or push them without separating task scope.

## Exact starting state

- Repository: `/Users/divy/code/personal/renewablesinfo/scr_climate_data`
- Branch: `agent/scr-dashboard-multi-asset-interactions`
- HEAD: `60f408749ebb896a2ec1377f8861876801f0e8d8`
- Upstream: `origin/agent/scr-dashboard-multi-asset-interactions`; local is three commits ahead.
- PR: none inspected or created for this task.
- Working tree: dirty. Task-scoped files listed below are uncommitted; unrelated/pre-existing dashboard, output-example, ZIP, profile, image, and other files also exist and must be preserved.
- Data release: published and verified in GCS.
- Code/docs release: local only; not committed or pushed.
- Platform release: not implemented; no database or Platform service changed.

## Read first

1. `runs/2026-08-18__solar_conus_overall_delta_v1/README.md` — concise consumer contract, process diagram, counts, and caveats.
2. `runs/2026-08-18__solar_conus_overall_delta_v1/manifest.json` — immutable identifiers, hashes, source/grid identity, cloud execution, and donor statistics.
3. `runs/2026-08-18__solar_conus_overall_delta_v1/qa_report.json` — complete acceptance evidence and final column list.
4. `docs/scr_profile/plans/SCR Solar CONUS Physical Delta Parquet Plan.md` — V1 plan and completion boundary.
5. `docs/scr_profile/discussions/conus_solar_physical_delta/03_full_overall_delta_distribution.md` — full factor distribution and tiny-denominator evidence.
6. `cloudrun/scr_physical_delta/README.md` — Cloud Run/runtime storage architecture and reuse warning.
7. `scripts/build_solar_overall_delta_parquet.py` — canonical-grid normalization and nearest-donor implementation.
8. `docs/scr_profile/SCR InfraSure scope.md` — broader SCR-to-InfraSure integration scope.

## Safe next action

The safest immediate action is a read-only team review, not another execution:

1. Open the delivery README, manifest, and QA report.
2. Confirm that `factor_filled` should screen the intended InfraSure physical-loss or cash-flow field and that `factor_raw`/imputation lineage must remain available.
3. Review the extreme-ratio examples and decide whether a later Platform version needs a denominator floor, cap, or compression.
4. Stop if the team has not chosen the target financial field or guardrail policy; do not implement those semantics by assumption.
5. Only after approval, write the Platform ingestion contract or create a new immutable asset run for Wind/Gas/BESS.

## Verification / repro

From:

```text
/Users/divy/code/personal/renewablesinfo/scr_climate_data
```

run:

```bash
/Users/divy/code/work/infrasure_git_codes/Hazard_modeling/.venv/bin/python - <<'PY'
import json
import pyarrow.parquet as pq
from pathlib import Path

root = Path('runs/2026-08-18__solar_conus_overall_delta_v1')
manifest = json.loads((root / 'manifest.json').read_text())
qa = json.loads((root / 'qa_report.json').read_text())
table = pq.read_table(root / manifest['output_file'], columns=['cell_id', 'factor_filled'])
print(qa['status'], table.num_rows, len(set(table['cell_id'].to_pylist())), table['factor_filled'].null_count)
print(manifest['output_sha256'])
PY
```

Expected:

```text
passed 418720 13085 0
1f087bf8a7959a8ae5c33c7b27a064e22433791fc57011aa24c4a2deaef5c482
```

External read-only verification:

```bash
gcloud run jobs executions describe scr-solar-overall-delta-v1-b4wgd \
  --region=us-central1 \
  --format='value(status.succeededCount,status.completionTime)'

gcloud storage ls -l \
  'gs://infrasure-scr-data/derived/solar_overall_delta_v1/run_id=20260818T160023Z/*'
```

Expected: `128`, completion `2026-08-18T16:15:52.414059Z`, and exactly four published objects.

## Files and artifacts

- `runs/2026-08-18__solar_conus_overall_delta_v1/scr_solar_conus_overall_delta_v1.parquet` — generated, local, untracked final Parquet; 23,058,501 bytes.
- `runs/2026-08-18__solar_conus_overall_delta_v1/manifest.json` — generated, local, untracked release manifest.
- `runs/2026-08-18__solar_conus_overall_delta_v1/qa_report.json` — generated, local, untracked acceptance report.
- `runs/2026-08-18__solar_conus_overall_delta_v1/README.md` — local, untracked consumer/run documentation.
- `runs/2026-08-18__solar_conus_overall_delta_v1/cloud/20260818T160023Z/` — local, untracked source and smoke inventories; no raw workbooks.
- `cloudrun/scr_physical_delta/run_task.py` — local, untracked task parser; current SHA adds overwrite protection and differs from the successful execution's parser by that guard only.
- `cloudrun/scr_physical_delta/README.md` — local, untracked Cloud Run operating note.
- `scripts/build_solar_overall_delta_parquet.py` — local, untracked final builder.
- `notebooks/conus_solar_physical_delta/` — local, untracked investigation code/evidence.
- `docs/scr_profile/discussions/conus_solar_physical_delta/` — local, untracked discussion evidence.
- `docs/scr_profile/plans/SCR Solar CONUS Physical Delta Parquet Plan.md` — local, untracked living plan.
- `docs/scr_profile/SCR InfraSure scope.md` — tracked file with uncommitted task-related changes.
- `docs/extra/tasks_history/2026-08-18__scr-climate-data__solar-conus-delta-cloudrun/` — local, untracked task-history package.
- `gs://infrasure-scr-data/derived/solar_overall_delta_v1/run_id=20260818T160023Z/` — externally published and verified data release.
- `gs://infrasure-benchmark/scr_climate_data/dev/cloudrun/solar_overall_delta_v1/run_id=20260818T160023Z/` — external runtime staging/evidence; retained, not authoritative.

## Guardrails / do not

- Do not rerun `scr-solar-overall-delta-v1` against the completed output prefix. Use a new run ID and immutable prefix.
- Do not overwrite `factor_raw` with imputed values or remove donor lineage.
- Do not call this a hazard-specific factor surface; V1 is overall `adjustedTotalDamage` only.
- Do not add ISO/RTO to this artifact; join it from the current canonical reference layer if needed.
- Do not silently cap, compress, floor, or discard extreme ratios.
- Do not treat benchmark staging as source truth.
- Do not delete the 1.8 GiB staging prefix without explicit owner approval and a resolved retention/access decision.
- Do not broadly stage, commit, push, clean, or delete the mixed working tree.
- Never include the previously shared credential in docs, commands, commits, logs, or future prompts.

## Open risks and decisions

- Which exact InfraSure loss/cash-flow field is compatible with `factor_filled`?
- Should Platform retain both raw and filled factors, or consume a view that exposes both?
- Does the factor need a denominator floor, ceiling, or log compression before Platform use?
- Should the Cloud Run service account receive read-only access to `infrasure-scr-data`, or should run-specific staging remain the standard?
- Who may authorize deletion of the retained benchmark staging copy?
- Should the 23 MB Parquet be committed, stored only in GCS, or managed through a data-artifact/LFS policy?
- Which asset class is next: Wind, Gas, or BESS, and are the SCR workbook schema/coverage equivalent?

## Requested outcome from the next model

Do not rerun Solar. After the owner/team chooses the next objective, produce one of these bounded outputs:

1. a reviewed Platform ingestion contract mapping `factor_filled`, `factor_raw`, scenario, horizon, and provenance to an approved InfraSure financial field; or
2. a new immutable Cloud Run plan and one-file smoke for exactly one next asset class, preserving the Solar V1 grain and QA gates.

In either case, keep Solar V1 unchanged and re-verify the published manifest/QA before relying on it.

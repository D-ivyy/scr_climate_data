# Task Context — SCR Solar CONUS Overall Physical-Damage Delta V1

## Outcome

**Verified complete externally and locally; repository changes remain uncommitted.** SCR Solar physical-risk workbooks were normalized into a 418,720-row Parquet covering all 13,085 canonical InfraSure served-CONUS cells, both SCR scenarios, and every five-year horizon from 2025 through 2100. The 1,157 cells without workbooks were filled from their geographically closest observed canonical cell while retaining raw-null and donor-lineage fields. Cloud Run execution `scr-solar-overall-delta-v1-b4wgd` completed 128/128 tasks, final QA passed, and the four-file delivery was published to:

```text
gs://infrasure-scr-data/derived/solar_overall_delta_v1/run_id=20260818T160023Z/
```

## Objective and scope

The objective was to create the first complete SCR-to-InfraSure screening surface for Solar PV:

```text
SCR adjustedTotalDamage at future horizon
                    /
SCR adjustedTotalDamage at 2025
                    =
positive overall physical-damage change factor
```

In scope:

- reconcile the SCR workbook population to InfraSure's canonical 13,085-cell grid;
- test availability and spatial/horizon behavior of the overall physical-damage delta;
- establish a deterministic missing-cell method;
- extract all observed workbooks through reusable Cloud Run fanout;
- build one traceable Parquet with observed and filled values kept distinct;
- validate and publish the delivery with manifest and QA evidence.

Out of scope for V1:

- rerunning the 1,157 missing SCR requests;
- hazard-specific production multipliers;
- ISO/RTO enrichment;
- a denominator floor, ceiling, cap, or log compression;
- client-facing or pricing-grade claims;
- Wind, Gas, or BESS production runs;
- direct InfraSure Platform/database ingestion.

## Background

The team wants to use SCR as a screening overlay rather than rerun InfraSure hazard models. The useful output is the climate-change movement in SCR's asset-specific physical damage, applied later to a compatible InfraSure financial loss metric. Earlier work established the conceptual scope and reviewed small workbook samples; this task tested the full Solar population and produced the canonical CONUS delivery.

The canonical grid is:

```text
/Users/divy/code/work/infrasure_git_codes/Hazard_modeling/
  data/hazard_conus_grid/common/benchmark_grid/
  served_conus_cell_ids_v2026_06.csv
```

Grid SHA-256:

```text
4e6f8efe5ad7834c832d06306aa6e730405fb93f7bdf6374ea219aaaa57d3df7
```

## Problems and root causes

1. **The SCR source was incomplete relative to the canonical grid.** The source bucket contained 11,928 valid canonical Solar workbooks, leaving 1,157 of 13,085 cells absent. The owner explicitly chose not to retry them for V1.

2. **Ratios can become extreme at tiny 2025 baselines.** The full distribution includes a maximum factor of `1556.7451149210062`. This is a denominator effect retained for review, not an imputation error. No guardrail was approved.

3. **Local workbook extraction was computationally heavy.** Ten local parser shards were projected to require roughly 45–50 minutes and sustained local load. Work was moved to Cloud Run at the owner's request.

4. **The Cloud Run runtime account could not read the SCR bucket.** The first execution failed with `storage.objects.get` denied for `project-service-account@modeling-nonprod-svc-db5x.iam.gserviceaccount.com`. Inputs were therefore frozen and staged under `gs://infrasure-benchmark/...` for runtime access; the original SCR bucket remains authoritative.

5. **The standard Cloud SDK image exposes `python3`, not `python`.** The first one-file smoke failed at the command boundary, was corrected, and the next smoke passed before full fanout.

6. **The repository already had a mixed dirty worktree.** Task-scoped work was preserved without staging, committing, pushing, cleaning, or attributing unrelated files.

## What changed

1. Investigated source/grid alignment, sample schema, availability, full factor distributions, denominator sensitivity, spatial behavior, and missing-cell patterns under `notebooks/conus_solar_physical_delta/`.

2. Updated the living scope and created focused discussion/plan documents under `docs/scr_profile/`.

3. Implemented a resumable local artifact-tool extractor for research/reference and a task-indexed Cloud Run extractor under `cloudrun/scr_physical_delta/`.

4. Cross-validated the Cloud parser against 500 artifact-tool workbook records; all schema, row-count, scenario, horizon, and total values matched exactly.

5. Implemented `scripts/build_solar_overall_delta_parquet.py` to join the extracted values to the canonical grid, choose closest observed donors by great-circle distance, preserve raw-versus-filled fields, and write the Parquet and manifest.

6. Added immutable output behavior: task uploads now require generation zero, so a repeated job cannot overwrite existing task evidence.

7. Produced the local delivery package under `runs/2026-08-18__solar_conus_overall_delta_v1/` and published it to the SCR derived-data prefix.

8. Removed the 1.8 GiB temporary local workbook cache after remote hash verification. The Cloud Run staging copy remains in GCS.

## Current state

- [x] 11,928/11,928 observed workbooks parsed without workbook errors.
- [x] 13,085 canonical cells present.
- [x] Exactly two scenarios: `ssp2-4.5` and `ssp5-8.5`.
- [x] Exactly 16 horizons: 2025–2100 in five-year steps.
- [x] Exactly 418,720 rows and 34 columns.
- [x] Exactly 32 rows per canonical cell.
- [x] Zero duplicate grain keys.
- [x] Exactly 1,157 imputed cells / 37,024 imputed rows.
- [x] Zero null `factor_filled` values.
- [x] Raw fields remain null on absent-workbook cells.
- [x] Every imputed factor equals the matching donor factor.
- [x] Every donor cell is an observed canonical cell.
- [x] 2025 `factor_filled` equals 1.0 for every row.
- [x] `iso_rto` is absent.
- [x] Cloud parser matched 500/500 artifact-tool reference records.
- [x] Cloud Run full execution completed 128/128 tasks in 5m15.52s.
- [x] Final Parquet was uploaded and downloaded again; local and remote SHA-256 matched.
- [ ] Task-scoped repository files are not committed or pushed.
- [ ] No production Platform/database ingestion has been implemented.
- [ ] No cap/compression/denominator-floor decision has been made.

## Files and systems

Task-scoped local files, currently uncommitted:

- `docs/scr_profile/SCR InfraSure scope.md` — living integration scope, modified.
- `docs/scr_profile/discussions/conus_solar_physical_delta/` — investigation, decisions, and full-distribution evidence, untracked.
- `docs/scr_profile/plans/SCR Solar CONUS Physical Delta Parquet Plan.md` — V1 production plan and completion state, untracked.
- `notebooks/conus_solar_physical_delta/` — investigations, outputs, and artifact-tool support parsers, untracked.
- `cloudrun/scr_physical_delta/` — reusable Cloud Run task parser and runtime notes, untracked.
- `scripts/build_solar_overall_delta_parquet.py` — final normalization/imputation builder, untracked.
- `runs/2026-08-18__solar_conus_overall_delta_v1/` — generated final Parquet, inventories, README, manifest, and QA report, untracked.
- `docs/extra/tasks_history/2026-08-18__scr-climate-data__solar-conus-delta-cloudrun/` — this handoff package, untracked.

External state, last verified 2026-08-18 at approximately 14:23 EDT:

- GCP project/region: `modeling-nonprod-svc-db5x` / `us-central1`.
- Cloud Run job: `scr-solar-overall-delta-v1`.
- Successful execution: `scr-solar-overall-delta-v1-b4wgd`.
- Runtime staging: `gs://infrasure-benchmark/scr_climate_data/dev/cloudrun/solar_overall_delta_v1/run_id=20260818T160023Z/`.
- Published delivery: `gs://infrasure-scr-data/derived/solar_overall_delta_v1/run_id=20260818T160023Z/`.
- Published objects: README, manifest, QA report, and Parquet; 23,066,865 bytes total.

## Verification evidence

- `qa_report.json` — status `passed`; all 18 recorded checks true.
- Parquet SHA-256 — `1f087bf8a7959a8ae5c33c7b27a064e22433791fc57011aa24c4a2deaef5c482` locally and after remote re-download.
- QA report SHA-256 — `68b88154c775cc540cda5d022c2f47601ed53a103a9742c14b5460bd8450c2f1`.
- Local manifest SHA-256 — `498540767f6e3a142a966db4193114b40c2f8c78d754470ba264837b0d7a3daf`.
- Cloud execution status — `Completed=True`, `succeededCount=128`, completion `2026-08-18T16:15:52.414059Z`.
- Remote Parquet object — size `23,058,501` bytes, generation `1787069871252066`.

## Known issues and risks

- The staging prefix duplicates roughly 1.8 GiB of raw source workbooks because the runtime service account lacks direct SCR-bucket read access. It was not deleted.
- `factor_filled` is a screening factor, not a client-facing or pricing-grade adjustment.
- The factor range is `0.03947368421052631` to `1556.7451149210062`; extreme tiny-baseline ratios remain uncapped.
- Nearest-cell fill is intentionally simple. Donor distance is 21.76 km median, 35.23 km P95, and 86.55 km maximum.
- The successful execution used parser SHA `424a2e...`. The job was subsequently updated to current parser SHA `1c9e4f...`, which adds generation-zero protection for future task-output uploads.
- The current job still points at the completed output prefix. Re-running it should fail rather than overwrite existing outputs; a new asset/run requires a new run ID and prefix.
- Repository history does not yet contain these task files. The current branch is three local commits ahead of its upstream and also contains unrelated dirty/untracked work.

## Next steps

1. Review the delivery README, manifest, QA report, factor distribution caveat, and proposed Platform use with the team before implementing ingestion.
2. Decide which compatible InfraSure loss/cash-flow field `factor_filled` may screen and whether the Platform needs both raw and filled factors.
3. Decide whether a denominator floor, cap, or compression is necessary; do not infer one from the extreme maximum alone.
4. For Wind, Gas, or BESS, create a new immutable run ID, validate the asset-specific workbook schema, perform a one-file Cloud Run smoke, and never reuse the Solar output prefix.
5. Resolve runtime access deliberately: either grant the Cloud Run service account read-only access to the SCR source bucket or stage a frozen, hashed run-specific inventory as done here.
6. Commit and push only after separating these task files from unrelated worktree changes and receiving the appropriate publication instruction.

## Provenance

- Repository: `/Users/divy/code/personal/renewablesinfo/scr_climate_data`
- Branch: `agent/scr-dashboard-multi-asset-interactions`
- HEAD: `60f408749ebb896a2ec1377f8861876801f0e8d8`
- Upstream: `origin/agent/scr-dashboard-multi-asset-interactions`
- Divergence at reconciliation: upstream behind local by three commits (`0 behind / 3 ahead`).
- PR: none inspected or created for this task.
- Documentation last reconciled: `2026-08-18 14:25 EDT` (`America/New_York`).

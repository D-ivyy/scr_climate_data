# Task Context — SCR Solar Overall-Factor Stabilization V2

## Outcome

- **Published and verified GCS research delivery:** Solar V2 preserves the complete V1 factor surface and adds an arctangent soft-log stabilized candidate with an unchanged `0.333333×–3×` identity band and a `5×` asymptotic ceiling.
- **Not a Platform production approval:** representative InfraSure EAL/TIV calibration, Wind/Gas replication, and client-facing use remain pending.

## Objective and scope

The task began after the raw Solar overall-damage factor was found to reach
`1,556.745×`. The goal was to determine whether hazard-level decomposition,
denominator floors, spatial replacement, or nonlinear compression could create
a numerically stable expected-loss screening factor without hiding the raw SCR
result.

In scope:

- diagnose the extreme tail using total and hazard-level workbook evidence;
- compare transformation families across all observed Solar cells, scenarios,
  and horizons;
- select a numerical candidate only after comparative testing;
- publish a new immutable V2 artifact with raw and candidate fields; and
- document the release, validation, limitations, and resumption path.

Out of scope:

- PML or TVaR scaling;
- an approved client-facing financial adjustment;
- changing InfraSure Platform code or a database;
- claiming the 3× start or 5× ceiling is scientifically learned from SCR; and
- adopting the same parameters for Wind or Gas without separate testing.

## Background

V1 defines the factor as:

```text
abs(future adjustedTotalDamage) / abs(2025 adjustedTotalDamage)
```

V1 contains 418,720 rows across 13,085 canonical cells, two scenarios, and
sixteen horizons. It is complete after nearest-observed-cell fill for 1,157 SCR
source-missing cells, but it intentionally retained the raw extreme ratios.

## Problems and root causes

1. **The raw overall ratio is unstable in the far tail.** The 2100 maximum is
   `649.427×` under SSP2-4.5 and `1,556.745×` under SSP5-8.5.
2. **Hazard decomposition explains but does not remove the problem.** Some
   outliers combine a tiny baseline with a newly nonblank future hazard, but a
   targeted high-outlier sample also contained like-for-like Wind factors up to
   `201.85×`.
3. **A denominator floor is insufficient.** The tested `1e-4` floor changed
   20.69% of rows, left a `61.36×` maximum, and introduced 29 scenario-order
   reversals.
4. **Spatial replacement is not a neutral financial rule.** Full 3×3 spatial
   smoothing changed 57.29% of rows and introduced 9,988 temporal and 6,342
   scenario reversals. Targeted replacement changed fewer rows but still
   introduced reversals.
5. **The first smooth-ceiling implementation saturated too quickly in
   float64.** A `tanh` V2 build was stopped by QA because distinct sufficiently
   large factors could become numerically identical near the 5× asymptote.

## What changed

1. Added a reproducible 15-method comparison over 11,928 observed cells, two
   scenarios, and all sixteen horizons.
2. Documented raw behavior, hazard evidence, transformation tradeoffs,
   mappings, distribution effects, and financial stress tests.
3. Selected `symmetric_piecewise_soft_log_arctan` as the leading numerical
   candidate:
   - identity band: `0.333333×–3×`;
   - upper asymptote: `5×`;
   - lower reciprocal asymptote: `0.20×`.
4. Built V2 from immutable V1 and appended raw/filled stabilized candidates,
   percent changes, compression flags, method parameters, source schema, and
   approval status.
5. Published README, QA report, Parquet, and manifest to a new immutable GCS
   run prefix, uploading the manifest last.

## Current state

- [x] V1 remains unchanged; its SHA-256 still equals `1f087bf8a7959a8ae5c33c7b27a064e22433791fc57011aa24c4a2deaef5c482`.
- [x] V2 contains 418,720 unique keys and 46 columns.
- [x] Every non-schema V1 column matches V2 exactly.
- [x] `factor_filled_stabilized_candidate` has zero nulls.
- [x] The identity band is exactly preserved.
- [x] The transform is strictly monotonic for all distinct raw and filled values.
- [x] QA passed and local/remote checksums match.
- [x] Four objects are published under the immutable V2 GCS prefix.
- [ ] Representative InfraSure Solar EAL/TIV records have not been tested.
- [ ] Wind and Gas factor distributions have not been run through this study.
- [ ] Platform ingestion and client-facing use are not approved.

## Files and systems

- Created locally, untracked: `scripts/build_solar_overall_delta_v2.py` — V1-to-V2 governed builder.
- Created locally, untracked: `notebooks/conus_solar_physical_delta/03_factor_stabilization_experiment.py` — comparative experiment.
- Generated locally, untracked: `notebooks/conus_solar_physical_delta/outputs/2026-08-18/factor_stabilization/` — CSV/JSON evidence.
- Created locally, untracked: `docs/scr_profile/discussions/conus_solar_physical_delta/04_factor_stabilization_experiment.md` — living investigation report.
- Generated locally, untracked: `runs/2026-08-18__solar_conus_overall_delta_v2/` — four-file V2 release package.
- Published and verified GCS research delivery: `gs://infrasure-scr-data/derived/solar_overall_delta_v2/run_id=20260818T193139Z/`.
- No Platform database, service, dashboard, or client-facing output was changed.

## Verification evidence

- Comparative experiment: 15 methods completed successfully over the full observed Solar corpus.
- Parquet QA: 418,720 rows, 46 columns, 418,720 unique keys, zero filled-candidate nulls.
- Source parity: zero non-schema V1 column differences.
- Candidate range: `0.2100840851×–4.9162049084×` for values present in this dataset.
- Compressed rows: 624 observed raw rows; 626 complete-grid rows.
- Parquet SHA-256: `864c1aa2f796fdcf04bc4d4c012ec9793dd356445d1fdb8d59ccde44a301af1e`.
- Remote verification: re-downloaded all four GCS objects and matched Parquet, QA, and README hashes to the manifest.

## Known issues and risks

- The transform is numerically justified, not calibrated to actual InfraSure
  loss economics. A 5× asymptote is an explicit screening policy choice.
- The symmetric lower bound is also a policy choice; it prevents extreme loss
  reductions but needs owner review.
- Solar results do not establish that Wind and Gas need the same parameters.
- The repository working tree is mixed and dirty; task files are uncommitted and
  unrelated/pre-existing changes must not be broadly staged or cleaned.

## Next steps

1. Join a small representative Solar asset sample to current InfraSure EAL and
   TIV, calculate raw versus candidate future EAL rates, and review every
   compressed case before any Platform ingestion contract is approved.
2. Repeat the same distribution experiment for Wind and Gas.
3. Decide whether parameters are universal or asset-class-specific.
4. Only then define the Platform consumer contract for
   `factor_filled_stabilized_candidate`.

## Provenance

- Repository: `/Users/divy/code/personal/renewablesinfo/scr_climate_data`
- Branch/commit: `agent/scr-dashboard-multi-asset-interactions` at `60f408749ebb896a2ec1377f8861876801f0e8d8`; branch is three commits ahead of its upstream.
- PR/commit for this task: none; local code/docs/run files are uncommitted.
- GCP project: `modeling-nonprod-svc-db5x`.
- Documentation reconciled: 2026-08-18 15:35 EDT.

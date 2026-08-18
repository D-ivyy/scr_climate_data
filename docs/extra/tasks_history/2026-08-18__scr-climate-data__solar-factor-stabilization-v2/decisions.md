# Decisions — SCR Solar Overall-Factor Stabilization V2

## 1. Preserve V1 and publish V2 separately

**Decision:** Keep Solar V1 immutable and publish the stabilized candidate under
a new V2 schema and run-specific GCS prefix.

**Rationale:** V1 is the audited raw research surface. Replacing its factors
would destroy provenance and make the transformation invisible.

**Alternatives considered:** Overwrite the V1 Parquet or replace
`factor_filled` in place. Both were rejected.

**Consequences / revisit trigger:** Consumers must choose raw V1 fields or V2
candidate fields explicitly. Never silently redirect a V1 URI to V2.

## 2. Keep the overall asset-level SCR factor as the main surface

**Decision:** Do not require a full hazard-weighted InfraSure calculation for
this release. Keep hazard evidence as diagnosis and QA.

**Rationale:** Hazard decomposition identified support changes, but like-for-like
Wind ratios still reached `201.85×`; granularity did not solve ratio instability.

**Alternatives considered:** Build future EAL by multiplying each internal
hazard EAL by an SCR hazard factor. This remains a future modeling option, not a
prerequisite for the screening surface.

**Consequences / revisit trigger:** Reopen if InfraSure adopts authoritative
hazard-level EAL allocations and SCR provides stable hazard-specific factors.

## 3. Use an arctangent soft ceiling in log-factor space

**Decision:** The V2 candidate uses
`symmetric_piecewise_soft_log_arctan`, with compression starting at `3×`, an
upper asymptote of `5×`, and reciprocal lower asymptote of `0.20×`.

**Rationale:** Among 15 tested methods/variants, this method changed only
0.164% of observed experiment rows, left the ordinary range unchanged, bounded
the extreme tail, preserved strict ordering, and introduced no temporal or
scenario reversals.

**Alternatives considered:** Hard cap, square-root/power compression, plain
logarithm, baseline floor, `tanh` soft ceiling, full spatial smoothing, and
targeted spatial replacement.

**Consequences / revisit trigger:** The 3× and 5× values are explicit policy
parameters. Reopen after representative EAL/TIV tests or if Wind/Gas show
materially different distributions.

## 4. Reject `tanh` as the published implementation

**Decision:** Do not publish the first `tanh` implementation.

**Rationale:** Its pre-publication QA found that float64 saturation could make
distinct sufficiently large inputs numerically identical near 5×. The
arctangent curve approaches the same bound more slowly and retained strict
ordering in the tested data.

**Alternatives considered:** Weaken the monotonicity QA or accept tail ties.
Both were rejected because the intended behavior is proportional compression.

**Consequences / revisit trigger:** Keep the failed attempt documented as a QA
lesson. Do not reintroduce it without a different numerical representation and
an explicit reason.

## 5. Preserve raw and filled factors alongside candidates

**Decision:** V2 appends candidate fields and compression flags; it does not
overwrite `factor_raw`, `factor_filled`, percent changes, donor lineage, or
source values.

**Rationale:** Users must be able to reproduce and audit every transformation,
and imputed values must remain distinguishable from observed values.

**Consequences / revisit trigger:** Any future schema may add fields, but it
must not remove raw inputs or lineage without a governed migration.

## 6. Treat spatial and hazard results as QA, not silent replacement

**Decision:** No spatial or hazard-based value replacement is included in V2.

**Rationale:** Spatial methods introduced time/scenario reversals and can erase
genuine localized risk. Hazard-level analysis is explanatory but not sufficient
to stabilize the factors.

**Consequences / revisit trigger:** Spatial statistics can be added as flags or
review evidence. Replacing values requires a separate approved model.

## 7. Limit the release approval boundary

**Decision:** V2 is approved only as a numerically validated screening
candidate and GCS research delivery.

**Rationale:** Synthetic EAL-rate stress tests demonstrate the bound but do not
validate actual InfraSure economics.

**Consequences / revisit trigger:** V2 is not approved for PML, TVaR, automatic
client-facing adjustment, or universal Wind/Gas use. Those uses require
explicit subsequent evidence and approval.

## 8. Publish immutably with manifest last

**Decision:** Use `run_id=20260818T193139Z`, generation-zero object writes, and
upload the manifest last.

**Rationale:** A partial upload cannot masquerade as a complete governed
release, and completed evidence must not be overwritten by a rerun.

**Consequences / revisit trigger:** Future releases require a new run ID and
prefix. Do not reuse this prefix.

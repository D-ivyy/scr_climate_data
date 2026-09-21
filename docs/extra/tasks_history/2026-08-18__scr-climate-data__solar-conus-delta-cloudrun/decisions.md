# Decisions — SCR Solar CONUS Overall Physical-Damage Delta V1

## 1. Use SCR's overall adjusted physical damage as the V1 factor basis

**Decision:** Use `adjustedTotalDamage` as the production V1 metric. Hazard-level fields remain research/QA evidence and are not rows in the final delivery.

**Rationale:** The integration goal is a simple asset-specific climate-change overlay for InfraSure financial loss analysis, not a replacement hazard model. SCR provides an overall asset-specific damage result for every returned Solar workbook/scenario/horizon, while individual hazard fields are structurally uneven.

**Alternatives considered:** Produce one factor per hazard or use combined damage/disruption/value impact. Hazard-level production factors would create many missing/structural cases, and disruption was not considered sufficiently useful for this scope.

**Consequences / revisit trigger:** The V1 Parquet must not be described as a hazard-by-hazard factor file. Revisit when the team chooses a specific hazard-level use case and validates hazard-specific coverage and semantics.

## 2. Define the factor against the same-scenario 2025 baseline

**Decision:** Compute:

```text
factor = abs(future adjustedTotalDamage) / abs(2025 adjustedTotalDamage)
```

for each SCR scenario independently. Preserve the signed SCR source values separately.

**Rationale:** SCR loss values use a signed convention, while InfraSure needs a positive multiplier. A same-scenario denominator makes the factor reproducible and avoids mixing scenario pathways. `Historical` was excluded because the overall total is blank.

**Alternatives considered:** Signed division, Historical baseline, cross-scenario baseline, or percent-only storage.

**Consequences / revisit trigger:** `factor_filled` is positive, `percent_change_filled = factor_filled - 1`, and the signed source values remain auditable. Reopen if SCR clarifies that 2025 has a different semantic role or provides a usable Historical total.

## 3. Deliver the full canonical grid at long scenario/horizon grain

**Decision:** One row per `cell_id × asset_type × scenario × horizon`, covering 13,085 cells, two scenarios, and sixteen 2025–2100 five-year horizons.

**Rationale:** This aligns directly with the existing InfraSure canonical grid and gives Platform consumers an explicit time/scenario coordinate without array-valued columns.

**Alternatives considered:** Observed cells only, a wide year-column layout, or a smaller regional pilot as the final artifact.

**Consequences / revisit trigger:** Solar V1 has exactly 418,720 rows. Any future asset delivery should preserve this grain unless a formal Platform storage contract selects a different representation.

## 4. Do not retry missing SCR requests in V1

**Decision:** Freeze source coverage at 11,928 observed workbooks and do not retry the 1,157 absent cells before delivery.

**Rationale:** The owner explicitly prioritized the completed Parquet and a simple fill over another vendor/request cycle.

**Alternatives considered:** Retry all missing cells, leave final factors null, or delay delivery.

**Consequences / revisit trigger:** Raw fields stay null for absent cells, and coverage provenance is essential. Reopen if a later SCR export materially reduces the missing population.

## 5. Fill each missing cell from one closest observed canonical cell

**Decision:** Select the geographically closest observed canonical cell by great-circle distance, with smaller `cell_id` as deterministic tie-breaker. Use that same donor for all scenarios and horizons of the target cell.

**Rationale:** It is deterministic, transparent, preserves a coherent donor time series, and matches the owner's request for the simplest defensible V1 completion.

**Alternatives considered:** Nearest-neighbor averaging, regional/state averages, interpolation, model-based filling, or no fill.

**Consequences / revisit trigger:** `factor_raw` remains null on imputed rows; `factor_filled`, `source_cell_id`, `donor_distance_km`, `fill_method`, and `is_imputed` carry the completed value and lineage. Revisit if validation against withheld observed cells shows unacceptable error or if maximum donor distance becomes materially larger for another asset class.

## 6. Apply no ceiling, compression, or denominator floor in V1

**Decision:** Preserve raw ratios without guardrails.

**Rationale:** The full distribution confirmed extreme small-denominator behavior, but no business or empirical threshold was approved. Silently choosing a cap would hide rather than resolve the modeling question.

**Alternatives considered:** Hard cap, log compression, denominator floor, or rejecting extreme cells.

**Consequences / revisit trigger:** The maximum remains `1556.7451149210062`; V1 is screening-only. Reopen after reviewing absolute 2025/future values and the intended InfraSure financial field.

## 7. Exclude ISO/RTO from this delivery

**Decision:** Omit `iso_rto` from the final Parquet.

**Rationale:** The field is not needed for the physical-damage delta objective, and the owner explicitly requested its removal.

**Alternatives considered:** Carry the canonical grid's existing ISO/RTO label for convenience.

**Consequences / revisit trigger:** Consumers needing market-region enrichment must join it from the current canonical spatial/reference layer rather than treating this SCR artifact as its owner.

## 8. Use Cloud Run Jobs for reusable workbook extraction

**Decision:** Run 128 task-indexed Cloud Run tasks with parallelism 32, using a frozen SHA-pinned source inventory and parser.

**Rationale:** Local parsing imposed sustained compute load and would recur for Wind, Gas, and BESS. Cloud fanout completed the full extraction in 5m15.52s after smoke validation.

**Alternatives considered:** Finish the ten-shard local run or build a custom image through Artifact Registry. The active account could not use Cloud Build/Artifact Registry, so the implementation used Google's standard Cloud SDK image plus a SHA-verified standard-library parser.

**Consequences / revisit trigger:** Every future asset should perform an artifact-tool equivalence check and one-file runtime smoke before fanout. A custom image can replace the standard image when build permissions and dependency governance are available.

## 9. Treat benchmark-bucket inputs as runtime staging, not source truth

**Decision:** Copy the frozen workbooks to a run-specific `infrasure-benchmark` prefix because the Cloud Run service account cannot read `infrasure-scr-data`.

**Rationale:** This unblocked the authorized Cloud Run execution without altering the original SCR bucket.

**Alternatives considered:** Change bucket IAM, use a different service account, or keep local execution. The active user lacked bucket IAM/service-account administration authority during the task.

**Consequences / revisit trigger:** The approximately 1.8 GiB staging copy remains and must not become authoritative. Reopen when the correct owner can grant least-privilege read access or approve staging cleanup.

## 10. Use immutable run prefixes and manifest-last publication

**Decision:** Publish to a unique run ID, upload the manifest last, and protect task-result writes with generation-zero preconditions.

**Rationale:** Partial or repeated executions must not masquerade as a complete delivery or overwrite evidence.

**Alternatives considered:** Mutable `latest` paths or overwriting a shared output folder.

**Consequences / revisit trigger:** Never rerun Solar against the completed output prefix. A new execution needs a new run ID and source inventory.

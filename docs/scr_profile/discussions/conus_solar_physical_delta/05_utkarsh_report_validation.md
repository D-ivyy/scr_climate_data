# Review of Utkarsh's SCR factor reports

**Review date:** 2026-08-25
**Decision status:** no V2 implementation change approved
**Question:** do the reports validate the observed SCR patterns, and does the
proposed hybrid additive–multiplicative method improve the current factor
implementation?

## What InfraSure is doing

The current Solar workflow deliberately separates the third-party climate
signal from InfraSure's own financial loss model:

```text
SCR adjustedTotalDamage
by cell × scenario × horizon
             |
             | divide by same-scenario 2025 value
             v
raw overall factor
             |
             | V2 leaves 0.333×–3× unchanged
             | and softly compresses only the tails
             v
stabilized screening factor
             |
             | multiply InfraSure's current Solar EAL
             v
climate-adjusted EAL screening view
```

The raw SCR values and raw factor remain available for audit. Only EAL is
scaled. PML, VaR, and TVaR are not scaled. The result is an internal screening
sensitivity, not a pricing or client-grade forecast.

The two reports answer different questions:

1. **Pattern validation:** Are factors below `1×` and cases where SSP2-4.5 is
   above SSP5-8.5 present in the source-derived surface, rather than created by
   our dashboard?
2. **Method change:** Does the zero/near-zero baseline problem require replacing
   or supplementing the V2 stabilized multiplier with an additive dollar loss?

## Report 1 — what is supported

Several central observations reproduce against the V2 Parquet:

- The stated 2050 and 2100 risk-reduction counts match the completed grid. For
  example, SSP2-4.5 has 410 cells at or below `0.995×` in 2050 and 488 in 2100.
- The 2050 scenario-crossover count of 897 cells matches when crossover means
  `factor(SSP2-4.5) - factor(SSP5-8.5) > 0.005`.
- The report's 2050 top-crossover table reproduces the **stabilized** V2
  factors. For example, New Jersey cell `287704` is `4.849×` under SSP2-4.5 and
  `2.013×` under SSP5-8.5.
- The patterns exist in the source-derived factor data before the dashboard
  renders them. They should not be silently forced to `1×` or reordered merely
  because SSP5-8.5 is expected to be larger everywhere.

This supports the limited conclusion that the patterns are not created by the
React dashboard or by converting a factor to EAL.

## Report 1 — what is not yet supported

The report is **not ready to serve as scientific attribution or final QA**:

1. Some headline crossover results do not reproduce from the current V2 data.
   The report gives 742 crossover cells in 2040 and 834 in 2070; the V2 query
   gives 701 and 728 using the stated `>0.5%` rule.
2. The reported mean and maximum crossover spreads are not reproducible from
   either raw or stabilized V2 factors. For the stabilized factors, the mean
   crossover spreads are approximately `2.96%` in 2040, `3.71%` in 2050,
   `6.47%` in 2070, `13.47%` in 2080, and `19.98%` in 2100.
3. The dollar EAL figures are not SCR-native values. They depend on an InfraSure
   Delivery EAL version, and at least one is inconsistent with the current
   payload: Michigan cell `270375` uses a stated baseline of `$635,659`, while
   the current Delivery payload contains approximately `$212,914`.
4. Geographic coherence is evidence that a pattern is systematic, but it does
   not prove the detailed causal explanations in the report. The claims about
   biomass limitation, hail melting, aerosols, tropical-cyclone wind shear, and
   jet-stream position are uncited and cannot be inferred from the overall
   `adjustedTotalDamage` field alone.
5. A conservative `max(SSP2-4.5, SSP5-8.5)` envelope may be a useful
   underwriting view, but it is a policy overlay. It must not overwrite the two
   source scenario paths.

**Assessment:** the report validates that reductions and scenario crossovers
are real features of the derived SCR surface, but its counts, dollar examples,
and physical explanations need revision or explicit source/version citations.

## Report 2 — the important idea

The report correctly identifies a general mathematical limitation:

```text
future = baseline × factor
```

cannot generate a nonzero future loss when the financial baseline is exactly
zero. It also correctly warns that a very small denominator can create an
enormous ratio even when the absolute SCR movement is small.

This is why V2 already preserves all of the following:

- baseline and future SCR damage magnitudes;
- absolute SCR damage movement;
- the raw ratio;
- the stabilized candidate ratio; and
- a flag showing whether compression occurred.

## Why the proposed dollar-offset rule cannot be implemented as written

The report proposes:

```text
future EAL
  = current InfraSure EAL × stabilized factor
  + emerging-hazard delta EAL in dollars
```

That formula requires the second term to be a calibrated dollar EAL. The SCR
source field is `adjustedTotalDamage`; its exact unit, annualization semantics,
and relationship to TIV are still vendor-confirmation items. A difference
between two SCR values therefore cannot yet be added to InfraSure EAL as
dollars.

There is also a baseline mismatch:

- all 11,928 observed Solar workbooks have a nonzero 2025 overall SCR value;
- the current 13,085-cell InfraSure Solar Delivery has **no** baseline EAL below
  `$100`; its minimum is approximately `$2,282.78`;
- the extreme ratios arise in the SCR denominator, not in a zero-dollar
  InfraSure EAL denominator; and
- a `$100` rule would therefore change zero current Solar cells.

The existing V2 surface contains 418,720 cell/scenario/horizon rows. Compression
changes 626 rows (`0.1495%`) across 85 distinct cells. Only 197 of those rows
have an SCR baseline magnitude below `1e-4`; 429 occur at or above `1e-4`.
Thus, the tail is not explained by one universal near-zero threshold.

### Concrete edge case

For New Jersey cell `287704`, SSP2-4.5 in 2050:

```text
SCR 2025 magnitude      0.000000405946
SCR 2050 magnitude      0.000038241552
raw factor             94.204×
V2 candidate factor     4.849×
current InfraSure EAL  about $550,114
```

The current screening calculation can produce a candidate EAL by multiplying
`$550,114 × 4.849`. An additive alternative cannot be computed defensibly until
we know whether the SCR movement `0.000037835606` is a fraction of TIV, another
normalized score, an annualized damage quantity, or something else.

## Other proposals that should remain separate

- **Hazard-level scaling:** potentially useful later, but current SCR hazard
  coverage is uneven and the governed delivery is intentionally the overall
  asset damage factor. Hazard disaggregation is not a drop-in fix for the
  overall-factor denominator problem.
- **TIV ceilings:** a financial-policy guardrail, not a correction to the SCR
  source. Current V2 does not scale PML, VaR, or TVaR.
- **Clamp at 2055:** an underwriting/product-horizon choice. Keep 2060–2100 in
  the research data even if a particular workflow displays only asset-life
  horizons.
- **Suppress large raw factors:** the UI may foreground the stabilized value,
  but the raw value must remain available for audit.

## Current decision

Do **not** replace or republish V2 from the second report. Continue to use the
existing dual-field design for internal screening:

```text
factor_filled                         raw completed-grid audit factor
factor_filled_stabilized_candidate    current V2 screening candidate
filled_factor_was_compressed          explicit tail flag
baseline/future/absolute movement     diagnostic evidence
```

For a future asset whose InfraSure baseline EAL is genuinely zero, return an
explicit unsupported/zero-baseline status rather than inventing an additive
dollar loss from an unconfirmed SCR unit.

## Test required before adopting an additive method

The proposal is worth testing, but only after the unit gate is closed:

1. Obtain SCR confirmation of `adjustedTotalDamage` units, annualization,
   inflation treatment, and whether it is a fraction of constant asset value.
2. Define a near-zero rule on the SCR source magnitude separately from any rule
   on InfraSure dollar EAL. Do not translate `1e-4` into `$100` without a proven
   unit conversion.
3. On the 85 affected cells plus ordinary control cells, compare:
   - raw multiplication;
   - current V2 stabilized multiplication; and
   - a separately labelled additive or blended candidate, if units allow it.
4. Test continuity at the threshold, scenario/time ordering, portfolio impact,
   EAL/TIV bounds, and sensitivity to the chosen threshold.
5. Review individual source workbooks for the largest absolute movements and
   largest ratios before approving any policy.

Until then, the report is a valuable proposal and caveat—not an implementation
specification.

## Reproducible evidence used

- `runs/2026-08-18__solar_conus_overall_delta_v2/scr_solar_conus_overall_delta_v2.parquet`
- `notebooks/conus_solar_physical_delta/outputs/2026-08-18/overall_delta_selected_horizon_outliers.csv`
- `/Users/divy/code/work/infrasure_git_codes/Hazard_modeling/dashboard/data/delivery_solar.grid.json`
  at Hazard Modeling commit `67dd36b2b95db71fa46a5259b5e94474bbdd3eec`
- V2 source fields and current dashboard formula documented in the SCR and
  Hazard Modeling repositories.
- Reproducible DuckDB queries:
  [`reviews/2026-08-25_utkarsh/validation_queries.sql`](reviews/2026-08-25_utkarsh/validation_queries.sql).

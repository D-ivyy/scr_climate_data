# SCR Solar CONUS overall-delta V2 candidate

## What we started with

V1 contains `418,720` rows for `13,085` canonical
cells, two SCR scenarios, and sixteen 2025–2100 horizons. Its overall factor is:

```text
factor_filled = |future adjustedTotalDamage| / |2025 adjustedTotalDamage|
```

V1 remains immutable. Its maximum raw factor is `1,556.745115×`.

## What V2 changes

V2 preserves the V1 raw, filled, imputation, donor, source, and location fields
and adds a numerically stabilized candidate factor:

```text
raw factor
    |
    +-- 0.333333× through 3× --> unchanged
    |
    +-- above 3× ------------> smooth arctangent log-space compression toward 5×
    |
    +-- below 0.333333× ------> reciprocal compression toward 0.20×
```

Primary candidate field:

```text
factor_filled_stabilized_candidate
```

Raw and filled factors remain available and are never overwritten.

## What this release provides

| Item | Value |
|---|---:|
| Rows | 418,720 |
| Canonical cells | 13,085 |
| Raw observed rows compressed | 624 |
| Complete-grid rows compressed | 626 |
| Candidate minimum | 0.210084× |
| Candidate maximum | 4.916205× |
| QA status | `passed` |

The candidate changes only the extreme tail while exactly preserving the
`0.333333×–3×` identity band and the ordering of distinct factor values.

## Status and permitted use

This is a **numerically validated screening candidate**. It is suitable for
InfraSure integration testing against expected-loss/EAL fields while retaining
the raw factor and audit flags.

It is not yet approved for:

- automatic client-facing financial adjustment;
- PML or TVaR scaling; or
- universal use across Wind and Gas before their distributions are tested.

The 3× start, 5× ceiling, and 0.20× reciprocal floor are explicit policy
parameters. Final financial approval requires representative EAL/TIV testing.

## Key columns

| Column | Meaning |
|---|---|
| `factor_raw` | Observed-cell V1 ratio; null for source-missing cells |
| `factor_filled` | Complete-grid V1 ratio after nearest observed-cell fill |
| `factor_raw_stabilized_candidate` | Stabilized observed-cell candidate |
| `factor_filled_stabilized_candidate` | Stabilized complete-grid candidate |
| `raw_factor_was_compressed` | Whether the raw observed factor changed |
| `filled_factor_was_compressed` | Whether the complete-grid factor changed |
| `factor_stabilization_status` | Approval boundary for the candidate |

## Validation

See `qa_report.json` for bounds, null behavior, source parity, identity-band,
monotonicity, row-count, and checksum checks. See `manifest.json` for immutable
source and release identifiers.

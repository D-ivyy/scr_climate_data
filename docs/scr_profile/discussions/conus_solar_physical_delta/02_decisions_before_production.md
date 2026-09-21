# Decisions before building the production Parquet

The evidence is strong enough to design the run, but four decisions should stay
explicit rather than being buried inside parsing code.

## 1. Which outputs are in V1?

Recommended:

```text
primary final factor   -> adjustedTotalDamage
hazard components      -> adjustedHazardDamage for QA only

not V1 factors         -> disruption
                       -> disruption damage equivalent
                       -> combined value impact
                       -> exposure ratings
```

Do not expand the V1 final Parquet across nine hazard names. Preserve hazard
components in staged QA evidence so `adjustedTotalDamage` can be reconciled and
the difference between a blank hazard and zero risk remains visible.

## 2. What should happen to the 1,157 missing workbooks?

Recommended sequence:

```text
missing canonical cell
        |
        v
retry/re-fetch from SCR
        |
        +-- recovered -> parse as observed source
        |
        +-- still absent -> preserve raw null + missing_source status
                                   |
                                   v
                         test optional spatial fill
```

Do not fill a structurally blank hazard metric. Spatial filling is eligible only
for a canonical cell whose complete source workbook is absent.

If a filled modeling surface is required, compare nearest-cell copy, local
median, and inverse-distance averaging through a masked-cell validation: hide
known cells, predict them from neighbors, and measure error by hazard, scenario,
horizon, and region. The selected method must keep `raw_factor` separate from
`filled_factor`, and record donor cells and distance.

## 3. What is a valid denominator?

Use 2025 within the same SCR scenario as the working baseline because historical
financial-impact fields are blank. Before production approval:

- confirm 2025 baseline semantics with SCR;
- inspect the full baseline distribution by hazard;
- define a near-zero rule from evidence;
- keep a factor null and status it when the denominator fails that rule.

A cap or logarithmic compression is an applied-model decision, not a source-data
cleanup. Always retain the uncapped factor.

## 4. How should the overall delta be used?

The overall physical-damage factor is the primary V1 asset-level screen because
it is populated more broadly than individual hazards. It should not be presented
as though all nine hazards were physically modeled.

Recommended product distinction:

| Surface | Use |
|---|---|
| Hazard-specific factor | QA and later research; not in the V1 final delivery. |
| Overall SCR damage factor | Primary asset-level screening surface after team approval. |
| InfraSure complete asset EL | Continue aggregating InfraSure hazard ELs with visible coverage labels. |

The team should approve which InfraSure asset-level loss metric this overall
factor may scale. It should not overwrite individual hazard EL values.

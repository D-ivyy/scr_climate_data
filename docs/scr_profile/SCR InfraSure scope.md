# SCR → InfraSure Scope

**Working title:** Asset- and Hazard-Specific SCR Climate Change Factors

**Status:** Execution scope for the controlled and regional validation with Divy, Prashant, and Utkarsh

**Date:** 2026-08-02 (updated from 2026-07-20)

**V1 objective:** Use SCR's change in hazard-level physical damage to scale InfraSure's current physical-damage expected loss without rerunning InfraSure's complete future hazard and damage models.

---

## 1. The decision in one sentence

For each supported asset and hazard, calculate the change in SCR's `adjustedHazardDamage` between a baseline and a future scenario/horizon, then apply that change directly to InfraSure's current physical-damage expected loss for the same asset and hazard.

```text
                          SCR result for this asset and hazard
                     baseline -----------------------> future
                                          |
                                          v
                                  SCR change factor
                                          |
                                          v
InfraSure current hazard EL ----------- multiply ---------> InfraSure future hazard EL
```

This is the intended shortcut. InfraSure does **not** need to run a complete future hazard simulation, reconstruct SCR's hazard maps, or reproduce SCR's damage functions for V1.

### The execution path agreed with the team

The work should move from a small controlled test to a larger regional test before any CONUS-scale build:

```text
6-10 controlled locations
  isolate location, asset type, value, geometry, and resilience
                    |
                    v
state or climate-region batch
  run the available 25 km x 25 km reference-cell center points
                    |
                    v
measure within-region and between-region variation
  test whether climate-region averages are representative
                    |
                    v
choose the smallest defensible lookup
  global factor | regional factor | spatial grid | per-asset SCR run
                    |
                    v
only then consider broader CONUS coverage
```

The regional batch is not a full CONUS implementation. It is the decision test that tells the team whether a broader grid is necessary at all.

## 2. Does this idea make sense?

Yes. It makes sense as a practical expected-loss scaling method, subject to a small set of tests before implementation.

SCR is useful because it does not give only a generic statement such as “wildfire risk rises 20%.” It analyzes a particular asset at a particular location and returns separate results for different hazards, scenarios, and future periods. The desired signal is therefore:

> For this asset, at this location, how much does SCR say this hazard's expected physical damage changes under the future climate case?

InfraSure can use that relative change while retaining its own current expected-loss number.

```text
What SCR contributes                    What InfraSure retains
--------------------                    ----------------------
future change by hazard                 current EL by hazard
location and asset context      x       InfraSure's financial baseline
scenario and horizon                    InfraSure reporting and aggregation
```

The value of this method is effort reduction:

```text
Full future-model route
climate data -> hazard model -> event set -> damage curves -> financial loss

SCR-delta route for V1
SCR baseline/future physical-damage result -> relative change -> scale InfraSure physical-damage EL
```

The second route is the intended scope.

## 3. The calculation we want

For asset `a`, hazard `h`, scenario `s`, and horizon `t`, first convert SCR's signed loss convention into loss magnitudes:

```text
SCR baseline magnitude = abs(adjustedHazardDamage(a,h,baseline))
SCR future magnitude   = abs(adjustedHazardDamage(a,h,s,t))

SCR Physical Damage Factor Raw(a,h,s,t)
    = SCR future magnitude / SCR baseline magnitude
      only when the baseline passes the baseline-validity check

SCR Physical Damage Absolute Change(a,h,s,t)
    = SCR future magnitude - SCR baseline magnitude

InfraSure Future EL(a,h,s,t)
    = InfraSure Current EL(a,h) x SCR Delta Applied(a,h,s,t)

SCR Damage Factor Applied = SCR Physical Damage Factor Raw
                            unless an approved guardrail is triggered
```

Using magnitudes is intentional because SCR exports damage as a negative loss. It does not erase the direction of change: a smaller future loss magnitude produces a factor below `1.0`, and a larger future loss magnitude produces a factor above `1.0`. A sign flip or positive credit is not a normal damage observation and must be flagged rather than silently converted.

The ratio is not calculated when the baseline is zero. For near-zero baselines, the implementer must preserve the absolute change, set the factor to null, and flag the row until the Phase 0 distribution review establishes an approved baseline floor. No numerical threshold or cap is adopted without evidence from the test data.

Illustrative example:

```text
Asset:                 Solar Plant A
Hazard:                Wildfire
SCR baseline impact:   0.80%
SCR 2050 impact:       1.00%

SCR wildfire delta:    1.00% / 0.80% = 1.25
Applied delta:         1.25 (passes validation; no guardrail needed)

InfraSure current
wildfire EL:           $100,000

InfraSure 2050
wildfire EL:           $100,000 x 1.25 = $125,000
```

The `$125,000` is an InfraSure result adjusted by an SCR-derived factor. SCR's raw percentage does not need to be shown as a competing client-facing loss estimate.

### Across the whole asset

There is no single SCR factor for the complete asset before the hazard results are calculated. Each hazard is adjusted separately, and the adjusted hazard ELs are then added using InfraSure's normal aggregation rule.

```text
                         SCR Delta        Future InfraSure EL
Current flood EL    x    Flood factor     =    Future flood EL
Current wind EL     x    Wind factor      =    Future wind EL
Current wildfire EL x    Wildfire factor  =    Future wildfire EL
                                                    |
                                                    v
                                      Future total asset expected loss
```

In the simplest additive case for the SCR-covered portion:

```text
Future modeled subtotal = sum(Future EL for each SCR-covered hazard)
```

If InfraSure uses dependency or correlation adjustments in its existing aggregation, those existing rules remain in place.

An uncovered hazard must not disappear from a complete asset total. Retain its current InfraSure EL in the arithmetic, but tag it as `uncovered_baseline_retained` so the Platform does not imply that SCR found no climate change:

```text
Complete future asset EL
  = scaled future EL for SCR-covered hazards
  + current InfraSure EL retained for uncovered hazards

Coverage label
  = modeled by SCR | baseline retained / future change unknown
```

If the Platform cannot show that distinction clearly, show the SCR-covered subtotal separately instead of presenting it as the complete future asset EL.

### Small guardrail caveat — ceiling or compression

A raw ratio can become unstable when the SCR baseline is very small or when an outlier is applied directly to InfraSure EL. The factor therefore needs a validation step before production use:

```text
raw SCR delta -> baseline/outlier check -> applied delta -> future InfraSure EL
```

The rule should remain simple:

- Always preserve the raw SCR delta.
- Reject or separately handle zero and near-zero baselines.
- Review the observed delta distribution across the initial examples before choosing any ceiling.
- If the factors are small and reasonable, use them unchanged.
- If extreme factors appear, use a documented hard ceiling/floor or soft/log compression and retain both the raw and applied values.

No numerical cap should be invented now. The initial asset/location examples must show whether a guardrail is needed and whether it should vary by hazard or horizon. Any compression must be visible and reproducible—not a hidden Platform adjustment.

## 4. What this scope is—and is not

### V1 is

- An **asset-specific, hazard-specific physical-damage change factor**.
- A way to scale InfraSure's current physical-damage expected loss.
- A baseline-to-future comparison by SCR scenario and horizon.
- A deliberately lightweight alternative to running complete future hazard models.
- A test-first project: determine the dimensions along which SCR's delta actually varies before building a large grid.

### V1 is not

- A rebuild of SCR's climate or hazard models.
- A full CONUS grid-processing project before the controlled and regional tests prove that spatial storage is needed.
- A replacement for InfraSure's current expected-loss calculations.
- A reconstruction of SCR's proprietary damage curves.
- A disruption, business-interruption, workability, or combined-value model.
- A generic multiplier applied to every hazard.
- A tail-risk adjustment unless SCR provides a separate defensible tail-change signal.

## What the SCR repository has already established

This scope starts from working evidence rather than proposing that work again:

- `export_scr_upload.py` already creates the SCR upload, private join-back manifest, and reject diagnostics.
- A returned physical workbook and transition workbook for one example gas-fired power asset are already stored and documented.
- `build_dashboard_data.py` already converts those returned workbooks into normalized JSON.
- The local dashboard already shows the overall physical trend and returned hazard-level damage, disruption, and value-impact curves.
- The current dashboard working tree also adds a direct hazard-trend view by scenario.
- Derived magnitude-response plots already exist, but they are correctly labeled as exploratory rather than official SCR vulnerability curves.

Therefore, V1 does **not** need another workbook-discovery dashboard. On 2026-07-21, a focused six-asset set was downloaded from the live SCR portal and added to the local dashboard. It now gives initial evidence on location and asset differences. It does **not** yet isolate every variable: the assets have different inputs, and the set is not a controlled national sample.

## 5. Questions that must be answered before implementation

These questions determine the size and usefulness of the project. They should be answered with a small test set before the team designs a national grid, production database, or Platform interface.

### Question 1 — Does the SCR delta actually vary by location?

This is the largest scope question.

SCR's absolute risk will clearly vary by location. What is not yet proven is whether the **relative baseline-to-future change** also varies materially by location.

```text
Hold constant:
  asset type + asset value + geometry + hazard + scenario + horizon

Change only location:

Location A  -> SCR delta = ?
Location B  -> SCR delta = ?
Location C  -> SCR delta = ?
Location D  -> SCR delta = ?
```

Possible outcomes:

```text
Is the delta materially different across locations?
        |
        +-- NO  -> Store one factor per hazard/scenario/horizon.
        |          No national SCR grid is needed for that factor.
        |
        +-- YES -> Store the factor by location or lookup cell.
                   Build spatial coverage only at the resolution justified
                   by the observed changes and the source data.
```

The external climate fields used by SCR have hazard-specific spatial resolutions. It is therefore plausible that some deltas repeat across many nearby assets while others vary materially. This must be measured rather than assumed.

The answer requires two tests, not one:

1. A controlled 6-10-location matrix to isolate the dimensions that drive the factor.
2. A state or climate-region batch using the available 25 km x 25 km reference-cell center points to measure spatial consistency and the error introduced by climate-region averaging.

Only the second test can support a decision about regional averaging or broader CONUS coverage.

### Question 2 — Which hazards provide a usable physical-damage delta?

The checked-in physical workbook contains eight hazard families and 28 continuous indicators:

```text
Drought       Flood          Heat          Landslide
Subsidence    Precipitation  Wildfire      Wind
```

However, “a hazard appears in the workbook” does not necessarily mean “SCR provides a usable `adjustedHazardDamage` delta for that hazard.”

The current evidence suggests:

| Hazard family | What is returned | Initial V1 interpretation |
|---|---|---|
| Flood | Inland/coastal depths plus `adjustedHazardDamage` for several sampled asset classes | Primary V1 candidate; flat results in some samples still require validation |
| Wind | Wind-speed indicators and a displayed damage function; numeric `adjustedHazardDamage` is sparse in the sample | V1 candidate only where baseline and future physical-damage values are populated |
| Wildfire | Burn probability, tree cover, FWI, and populated `adjustedHazardDamage` in sampled assets | Demonstrated V1 physical-damage candidate |
| Heat | Workability and disruption fields; direct structural damage is blank in the sample | Outside V1; retain as reference only |
| Drought | Water stress, duration, and magnitude indicators | Outside direct physical-damage V1 unless SCR later returns damage values |
| Precipitation | Maximum 1-day and 5-day precipitation indicators | Outside direct physical-damage V1; avoid double counting with Flood |
| Landslide | Susceptibility indicator | Outside direct physical-damage V1 |
| Subsidence | Rate indicator | Outside direct physical-damage V1 |
| Hail, tornado, winter weather | Not present in the example | Requires another source or remains explicitly uncovered |

The output must therefore be classified hazard by hazard:

```text
Hazard present
     |
     +-- Has baseline and future adjustedHazardDamage? --> V1 damage factor
     |
     +-- Has only continuous hazard indicator? ----> possible later factor,
     |                                               but outside direct-EL V1
     |
     +-- Not present? ------------------------------> supplementary source or
                                                     clearly not modeled
```

### First live evidence — six-asset portal test (2026-07-21)

The first multi-asset test supports a **per asset × hazard × scenario × horizon physical-damage factor**, not one universal scalar.

The two gas assets are the clearest initial location test. Their Flood physical-damage factor is flat at `1.00x`, while their 2100 Wildfire physical-damage factors differ: Whitehorn is approximately `1.00x` and Frederickson approximately `1.35x`. This is enough to reject a single global physical-damage factor, but not enough to determine the final spatial lookup resolution.

All six assets return the same eight hazard families as indicator/rating records, but numeric physical-damage coverage is much sparser. Therefore, **hazard present is not the same as physical-damage factor available**.

The dashboard may retain disruption, disruption damage equivalent, Heat workability, and combined value for research and reconciliation. V1 must not use those channels to scale InfraSure physical-damage EL.

### Question 3 — Does the delta vary by asset type?

The same location should be tested with at least a solar asset and a wind asset while holding asset value and resilience assumptions constant.

```text
Same location + same hazard + same physical-damage inputs

Solar asset -> future / baseline = ?
Wind asset  -> future / baseline = ?
```

- If the ratio is the same, the factor may be location-and-hazard specific but reusable across asset types.
- If the ratio differs, the factor includes SCR's asset vulnerability or operational assumptions and must retain `asset_type` as part of its key.

This is not necessarily a problem. An asset-specific hazard factor is one of the reasons SCR is useful. It simply changes how many factors InfraSure must store.

### Question 4 — Does the physical-damage delta change with asset value, geometry, or resilience inputs?

Run the same asset and location while changing one financial/input variable at a time.

```text
Configuration 1: value $100M, point geometry
Configuration 2: value $200M, point geometry
Configuration 3: value $100M, asset footprint
Configuration 4: same value/geometry, different resilience assumption
```

The ratio is portable only if it behaves predictably:

- A damage percentage should normally remain stable when only asset value changes.
- Geometry may change the mix of hazard intensity across the asset footprint.
- An adjusted result may depend on resilience measures.

Revenue is not a V1 factor dimension because V1 does not use disruption. If the physical-damage delta changes materially with value, geometry, or resilience, InfraSure should either retain those dimensions in the factor key or calculate SCR results directly for each new asset rather than use a generalized lookup.

### Question 5 — What is the correct baseline?

The checked-in workbook contains `Historical` plus 2025–2100 in five-year steps, but historical total-impact fields are blank in the example.

Before calculating ratios, SCR must confirm whether the denominator should be:

- `Historical` indicator or financial value;
- 2025 as the near-term financial baseline;
- another defined current-climate period; or
- a vendor-provided baseline field not yet identified.

```text
Do not calculate:
future financial impact / blank historical financial impact

Possible approved calculation:
2050 financial impact / 2025 financial impact
```

The baseline definition must remain attached to every factor.

### Question 6 — Is `adjustedHazardDamage` truly annualized expected physical loss?

We need vendor confirmation of:

- exact units;
- whether `adjustedHazardDamage` is an average annual asset-value impact or another financial measure;
- whether values are already adjusted for resilience;
- whether the future result is an inflation-neutral percentage of asset value/TIV or includes nominal price or inflation assumptions;
- how repeated hazard-level values relate to the indicator rows.

The repository currently preserves raw numbers because percent and basis-point displays have not been vendor-confirmed as the final units.

The applied factor must represent physical climate-risk change rather than future price inflation. If SCR returns a percentage of constant asset value, the ratio is likely inflation-neutral; if it incorporates nominal future currency assumptions, it cannot be applied directly to InfraSure EL without adjustment.

### Question 7 — Can the same delta be used for tail risk?

Not automatically.

```text
Expected-loss delta  -> valid candidate for scaling EL
Expected-loss delta  -X-> automatic scaling of PML, VaR, OEP, or AEP tails
```

Flood and Wind contain return-period hazard indicators, but that does not prove SCR returns return-period-specific **financial-loss** changes. V1 should therefore target expected loss. Tail scaling is a separate extension only if the source supports reconstructing the loss distribution or provides tail-specific factors.

### Question 8 — How should we use the overall asset curve versus the hazard curves?

The repository already exposes both:

```text
Overall asset curves
  adjustedTotalValueImpact
  adjustedTotalDisruption

Hazard-level curves
  adjustedHazardDamage
  adjustedHazardDisruption
  adjustedHazardDisruptionDamageEquivalent
  adjustedHazardValueImpact
```

They support two different deltas:

```text
Overall asset delta = total future impact / total baseline impact
Hazard delta        = hazard future impact / hazard baseline impact
```

The recommended use is:

- **`adjustedHazardDamage` by hazard:** the only primary V1 input for scaling InfraSure physical-damage EL.
- **Overall asset curve:** reconciliation and research only; it is not an approved fallback factor.
- **Disruption, DDE, Heat, and combined-value curves:** research and QA only.
- **Derived magnitude-response curve:** research and QA only unless SCR confirms it represents an official vulnerability relationship.

The example confirms that the overall curve contains multiple components:

```text
adjustedTotalValueImpact
  = adjustedTotalDamage
    + adjustedTotalDisruptionDamageEquivalent
```

At `ssp5-8.5 / 2100` in the example, the total value impact reconciles exactly to those two total components. The hazard rows also explain the composition: Flood and Wildfire contribute quantified value impact, while Heat contributes disruption damage-equivalent even though its hazard value-impact field is blank.

This matters because the overall asset curve includes disruption damage equivalent and can rise while a hazard's physical-damage result is flat. The overall curve must therefore **not** be reused as a physical-damage factor for Flood or any other hazard.

## 6. The minimum experiment and regional validation

Do not begin with every U.S. grid cell. Use the following two-stage test.

### Stage A — controlled matrix

Begin with a controlled matrix that isolates one dimension at a time.

### Test locations

Use approximately 6–10 locations selected to create meaningful contrast:

- High and low Flood exposure.
- High and low Wildfire exposure.
- Tropical-cyclone and extratropical-wind regions.
- Hot and temperate locations.
- At least two nearby locations to test whether factors repeat within a source cell or region.

### Test asset configurations

At each selected location, use:

1. Solar asset with fixed value and geometry.
2. Wind asset with the same value and geometry.
3. Solar asset with a changed value.
4. Solar asset with changed geometry or footprint.
5. One resilience-input variant if supported.

### Test dimensions held constant

For each comparison, preserve:

- Hazard.
- Scenario.
- Horizon.
- Baseline definition.
- SCR source/product version.
- All asset inputs except the one being tested.

### Analysis output

Produce one compact variance report:

```text
For each hazard/scenario/horizon:

location variation     = range and coefficient of variation across locations
asset-type variation   = solar delta versus wind delta at the same location
value sensitivity      = delta after changing only asset value
geometry sensitivity   = delta after changing only geometry or footprint
resilience sensitivity = delta after changing only resilience input
delta distribution     = median, range, extreme values, and near-zero baselines
```

The purpose is not to choose a universal numerical tolerance in advance. It is to see whether the differences are immaterial, regional, or strongly asset-specific.

### Stage B — larger state or climate-region batch

After Stage A works end to end, select one larger test area—a state, a climate region, or two contrasted climate regions—with meaningful Flood and Wildfire variation. Wind may be included where SCR returns populated physical-damage values.

1. Create one standardized solar configuration and one standardized wind configuration, subject to SCR asset-type availability.
2. Place the standard configurations at the center points of the available 25 km x 25 km reference cells in the selected region.
3. Keep value, geometry, resilience, scenarios, horizons, and baseline definition fixed.
4. Export the batch through the existing upload/manifest workflow.
5. Ingest the returned SCR workbooks and calculate raw factors only for valid baseline/future pairs.
6. For every hazard/scenario/horizon, calculate the climate-region average and the within-region spread.
7. Compare each cell factor with the regional average and identify clusters, discontinuities, flat cells, missing values, and outliers.
8. Decide whether the regional average is representative, whether subregional/spatial storage is necessary, or whether the signal is too unstable to operationalize.

```text
cell factors in selected region
          |
          +--> small within-region spread --> candidate regional factor
          |
          +--> stable spatial pattern ------> candidate cell/grid lookup
          |
          +--> asset-type split ------------> regional/grid x asset type
          |
          +--> unstable or sparse ----------> keep per-asset workflow or reject
```

The regional test must be completed before anyone builds a nationwide factor table. Expanding to broader CONUS coverage is a later implementation choice, not an assumption in this scope.

## 7. The four possible architectures

The test result—not an assumption—selects the architecture.

```text
Outcome A: delta does not vary materially by location or asset type

  Delta[hazard, scenario, horizon]
  -> smallest scope; no spatial lookup required

Outcome B: delta varies by location but not asset type

  Delta[location/cell, hazard, scenario, horizon]
  -> spatial lookup; reusable across assets

Outcome C: delta varies by location and asset type

  Delta[location/cell, asset_type, hazard, scenario, horizon]
  -> solar/wind-specific spatial lookup

Outcome D: delta also varies with value, geometry, or resilience

  Delta[asset configuration, hazard, scenario, horizon]
  -> generalized grid has limited value;
     process each new asset through SCR or retain a richer key
```

This decision is the main deliverable of the first phase. It tells us whether the project is a small factor table, a grid, an asset-class grid, or a per-asset SCR workflow.

## 8. Execution handoff and V1 scope

### Ownership

| Role | Responsibility |
|---|---|
| **Utkarsh — implementation owner** | Run the controlled and regional batches, preserve manifests and raw outputs, calculate the variance report, and deliver an architecture recommendation. |
| **Divy — model/product decision owner** | Select the initial region and standard asset configurations; approve baseline, decrease-factor, guardrail, hazard-coverage, and Platform presentation decisions. |
| **Prashant / SCR contact — dependency owner** | Close any unresolved SCR input requirements and confirm metric units, baseline semantics, loss-sign convention, inflation treatment, and usage/licensing constraints. |

### What Utkarsh needs to do now

```text
1. Freeze test configuration
   -> region, cell centers, standard assets, scenarios, horizons, baseline

2. Prove the controlled batch
   -> 6-10 locations; one-variable-at-a-time comparisons

3. Run the regional batch
   -> standardized assets at 25 km x 25 km cell center points

4. Join and calculate
   -> returned assetName -> private manifest -> InfraSure asset/location ID
   -> raw factor, absolute change, coverage status, guardrail status

5. Analyze spatial consistency
   -> cell values, regional average, spread, outliers, missingness

6. Recommend Architecture A, B, C, or D
   -> include evidence and estimated coverage/storage implications

7. Hand off reproducible artifacts
   -> configuration, upload, private manifest, raw SCR returns,
      normalized factor table, variance report, and decision summary
```

Utkarsh should not build the complete CONUS grid, select a production cap, or wire factors into client-facing EL until Divy reviews the regional evidence and approves the architecture.

### Phase 0 — Prove the delta

1. Confirm the `adjustedHazardDamage` definition and units.
2. Confirm the baseline and future-period semantics.
3. Confirm that physical-damage values are annualized asset-value impacts.
4. Confirm whether the metric is inflation-neutral and suitable for scaling a current-value InfraSure EL.
5. Run the controlled location/asset/input test matrix.
6. Run the selected state/climate-region batch at the available 25 km x 25 km reference-cell centers.
7. Quantify location, within-region, asset-type, value, geometry, and resilience sensitivity; compare between regions when the test includes more than one.
8. Classify each hazard as physical-damage capable, indicator-only, or unavailable.
9. Review zero/near-zero baselines and the observed delta distribution; propose a baseline floor and any ceiling/floor or soft/log compression only if supported by evidence.
10. Decide whether factors below `1.0` may reduce InfraSure EL or whether the applied underwriting factor has a conservative floor of `1.0`; always retain the raw factor.
11. Select Architecture A, B, C, or D.

### Phase 1 — Implement only the selected dimensions

1. Extend the existing workbook-to-JSON builder into the selected production ingestion path; do not rebuild the proven parser from scratch.
2. Join returned `Output.assetName` through the private manifest to the InfraSure asset ID.
3. Calculate and store the approved delta with its baseline, scenario, horizon, hazard, and necessary asset/location dimensions.
4. Retain the raw SCR workbook and values for reproducibility.
5. Do not build unused grid or asset dimensions.
6. Version the calculation logic and attach every record to its SCR batch run and portfolio/context where applicable.

### Phase 2 — Apply to InfraSure expected loss

1. Retrieve InfraSure current EL by asset and hazard.
2. Retrieve the matching SCR delta.
3. Calculate future EL.
4. Retain current EL for uncovered hazards with an explicit `uncovered_baseline_retained` status; do not describe the future change as zero.
5. Apply InfraSure's existing dependency/correlation aggregation rules where they exist. Otherwise, label a simple sum as an additive V1 subtotal rather than introducing a new compound-risk model.
6. Aggregate adjusted hazard ELs to the asset and portfolio.
7. Preserve current and future values separately.

```text
current_el
    x scr_delta_applied(asset/location, hazard, scenario, horizon)
    = future_el
```

### Phase 3 — Present in the Platform

Reuse the distinctions already demonstrated in the local SCR dashboard: overall asset trend, hazard-level trend, hazard ranking, and clear labeling of unquantified hazards.

Show:

- Current InfraSure EL.
- Future InfraSure EL.
- Absolute and percentage change.
- Hazard, scenario, horizon, and source.
- A clear missing-coverage status.

Do not show:

- An unlabeled SCR percentage beside an InfraSure percentage.
- A tail-risk result derived only from an EL multiplier.
- An uncovered hazard as unchanged.
- A universal asset factor that hides hazard-level differences.

## 9. V1 factor record

Store only the fields needed to reproduce and understand the change:

| Field | Purpose |
|---|---|
| `asset_id` or `location_id` | Determined by the spatial/asset-dependence test |
| `asset_type` | Required only if the delta varies by asset type |
| `hazard` | The specific hazard being scaled |
| `scenario` | Original SCR scenario |
| `baseline_period` | Exact denominator definition |
| `future_horizon` | Future comparison year/period |
| `scr_metric_name` | Exact source field; V1 is `adjustedHazardDamage` |
| `scr_baseline_value` | Preserved source denominator |
| `scr_future_value` | Preserved source numerator |
| `scr_delta_raw` | Future divided by baseline, preserved without modification |
| `scr_delta_applied` | Raw delta after any approved guardrail; equals raw delta when no guardrail is needed |
| `guardrail_status` | None, capped, compressed, rejected baseline, or manual review |
| `source_product_version` | Reproducibility |
| `raw_record_reference` | Link to the source row/workbook |
| `quality_status` | Approved, provisional, unavailable, or invalid baseline |
| `coverage_status` | SCR modeled, indicator-only, unavailable, or uncovered baseline retained |
| `scr_run_id` | Join to the reproducible batch-run directory and manifest |
| `portfolio_id` | InfraSure portfolio context where applicable |
| `created_at` | Factor-record creation timestamp |
| `schema_version` | Version of the factor-calculation and guardrail logic |

Value, geometry, and resilience belong in the key only if the experiment proves they affect the delta.

## 10. Acceptance criteria

The focused scope is complete when:

1. We know whether SCR's delta varies materially by location, based on both the controlled matrix and a larger state/climate-region batch.
2. We know whether it varies by asset type, value, geometry, or resilience.
3. Every InfraSure hazard is classified as physical-damage capable, indicator-only, unavailable, or not applicable.
4. `adjustedHazardDamage` and its baseline are documented for each V1 hazard.
5. At least Flood, Wind, and Wildfire have been evaluated for direct EL scaling.
6. Heat and disruption are explicitly excluded from the applied V1 factor.
7. Architecture A, B, C, or D has been selected from evidence.
8. One current-to-future InfraSure physical-damage EL calculation can be reproduced end to end.
9. The observed delta distribution has been reviewed and any ceiling/compression rule is documented; raw and applied deltas remain separate.
10. Tail metrics remain separate unless tail-specific evidence is approved.
11. Licensing permits storing derived deltas and using them in client-facing calculations.
12. The team has measured the error/spread around a climate-region average and decided whether regional averaging, a cell lookup, or per-asset processing is defensible.
13. Zero and near-zero baselines return an explicit status rather than an infinite or arbitrary multiplier.
14. Complete asset totals retain uncovered current EL with a visible coverage status, or the output is explicitly labeled as an SCR-covered subtotal.
15. Each result is traceable to a run, raw workbook row, schema version, and creation time.

## 11. Recommended decision

Approve the concept as an **SCR-derived, asset- and hazard-specific physical-damage expected-loss delta**.

Before building a national grid or a detailed integration, run the controlled and regional experiments to answer two primary questions:

1. Does the delta vary enough by location to require spatial storage?
2. Which hazards actually provide a usable `adjustedHazardDamage` delta?

Then test asset type and financial-input dependence. These results determine the smallest correct architecture. If a climate-region average is representative, use it. If not, retain cell-level or per-asset processing. A broader CONUS build is justified only after this decision.

The simplest intended product remains:

> SCR tells us how the expected physical damage from a particular hazard changes for a particular asset. InfraSure uses that relative change to scale its own current physical-damage EL, without rerunning the full future hazard and damage model.

---

## Sources and provenance

### Curated InfraSure meeting records

The scope was synthesized from internal SCR discussions with Prashant and Utkarsh. Those meeting records remain in the private InfraSure notes workspace and are not published in this repository.

### Dedicated SCR workspace evidence

- [SCR workflow guide](../guide.md)
- [Returned-output schema](../output_examples/schema.md)
- [Physical-risk example workbook](../output_examples/asset_1232_physical_risks.xlsx)
- [Transition-risk example workbook](../output_examples/asset_1232_transition_risks.xlsx)
- [ClimateMetrics metadata workbook](../metadata/climatemetrics_metadata.xlsx)
- [ClimateMetrics methodology](../metadata/climatemetrics_methodology.pdf)
- [ClimateMetrics FAQ](../metadata/climatemetrics_faq.pdf)
- [SCR dashboard-analysis decisions](../extra/tasks_history/2026-07-02__scr-climate-data__dashboard-analysis/decisions.md)
- [SCR dashboard-analysis handoff](../extra/tasks_history/2026-07-02__scr-climate-data__dashboard-analysis/handoff.md)
- [SCR local dashboard guide](../../dashboard/README.md)
- [Normalized example asset JSON](../../dashboard/data/example_asset_1232.json)
- [SCR dashboard data builder](../../scripts/build_dashboard_data.py)
- [SCR upload exporter](../../scripts/export_scr_upload.py)

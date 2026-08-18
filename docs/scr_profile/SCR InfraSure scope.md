# SCR → InfraSure Scope

**Working title:** Asset-Level SCR Overall Physical-Damage Delta

**Status:** Solar V1/V2 research delivery complete; InfraSure EAL/TIV calibration
and Wind/Gas replication pending

**Date:** 2026-08-18 (updated from 2026-07-20)

**V1 objective:** Use the change in SCR's overall physical-damage result,
`adjustedTotalDamage`, as an asset-level climate-change factor without rerunning
InfraSure's complete future hazard and damage models.

### Current execution status — 2026-08-18

```text
V1 raw/filled Solar surface       COMPLETE and published to GCS
  13,085 cells x 2 scenarios x 16 horizons
                     |
                     v
15-method stabilization test      COMPLETE
                     |
                     v
V2 arctangent soft-log candidate  COMPLETE and published to GCS
  unchanged 0.333333x-3x; approaches 0.20x/5x bounds
                     |
                     v
Representative InfraSure EAL/TIV calibration  PENDING
Wind/Gas replication                         PENDING
```

V2 is a numerically validated screening candidate, not a client-facing
financial approval. The raw V1 fields remain available and unchanged.

---

## 1. The decision in one sentence

For each standardized asset and location, calculate the change in SCR's
`adjustedTotalDamage` between 2025 and each future scenario/horizon. Deliver that
overall factor on the canonical grid. Hazard-level values remain QA and research
evidence, not the main V1 output.

```text
                          SCR overall damage for this asset
                     baseline -----------------------> future
                                          |
                                          v
                                  SCR change factor
                                          |
                                          v
InfraSure current asset EL ------------ multiply ---------> screened future asset EL
```

This is the intended shortcut. InfraSure does **not** need to run a complete future hazard simulation, reconstruct SCR's hazard maps, or reproduce SCR's damage functions for V1.

### The execution path agreed with the team

The Solar CONUS workbooks are now available, so the current execution path is:

```text
11,928 observed Solar workbooks
  exact join to the 13,085-cell canonical grid
                    |
                    v
extract adjustedTotalDamage
  preserve signed 2025 and future values
                    |
                    v
derive overall factor
  abs(future total damage) / abs(2025 total damage)
                    |
                    v
retain raw missing-source status for 1,157 cells
  fill the complete surface from one closest observed donor per cell
                    |
                    v
one 13,085-cell overall-delta Parquet
  scenario x horizon x standardized asset type
```

Regional and hazard-level views remain QA tools for understanding spatial
patterns and total composition. They are not additional V1 delivery dimensions.

## 2. Does this idea make sense?

Yes. It makes sense as a practical expected-loss scaling method, subject to a small set of tests before implementation.

SCR is useful because it analyzes a particular asset at a particular location
and provides a physical-damage rollup across the hazards it can financially
quantify. The desired V1 signal is therefore:

> For this standardized asset at this location, how much does SCR's overall
> modeled physical damage change under the future climate case?

InfraSure can use that relative change while retaining its own current expected-loss number.

```text
What SCR contributes                    What InfraSure retains
--------------------                    ----------------------
overall physical-damage change          current asset-level EL or loss metric
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

For asset `a`, location `l`, scenario `s`, and horizon `t`, first convert SCR's
signed loss convention into loss magnitudes:

```text
SCR baseline magnitude = abs(adjustedTotalDamage(a,l,s,2025))
SCR future magnitude   = abs(adjustedTotalDamage(a,l,s,t))

SCR Overall Physical Damage Factor Raw(a,l,s,t)
    = SCR future magnitude / SCR baseline magnitude
      only when the baseline passes the baseline-validity check

SCR Overall Physical Damage Absolute Change(a,l,s,t)
    = SCR future magnitude - SCR baseline magnitude

InfraSure Screened Future Loss(a,l,s,t)
    = InfraSure Current Asset Loss(a,l) x SCR Delta Applied(a,l,s,t)

SCR Damage Factor Applied = SCR Physical Damage Factor Raw
                            unless an approved guardrail is triggered
```

Using magnitudes is intentional because SCR exports damage as a negative loss. It does not erase the direction of change: a smaller future loss magnitude produces a factor below `1.0`, and a larger future loss magnitude produces a factor above `1.0`. A sign flip or positive credit is not a normal damage observation and must be flagged rather than silently converted.

The ratio is not calculated when the baseline is zero. All observed Solar 2025
totals were nonzero, but near-zero denominators produced an unstable raw tail.
V1 preserves that raw evidence. V2 preserves the same raw factor and provides a
separate stabilized candidate plus a compression flag; it never silently
replaces the source ratio.

Illustrative example:

```text
Asset:                 Solar Plant A
SCR 2025 total damage: 0.80%
SCR 2050 total damage: 1.00%

SCR overall delta:     1.00% / 0.80% = 1.25
Applied delta:         1.25 (passes validation; no guardrail needed)

InfraSure current
asset loss metric:     $100,000

InfraSure 2050
wildfire EL:           $100,000 x 1.25 = $125,000
```

The `$125,000` is an InfraSure result adjusted by an SCR-derived factor. SCR's raw percentage does not need to be shown as a competing client-facing loss estimate.

### Across the whole asset

The V1 delivery intentionally uses one overall SCR physical-damage factor for
the complete standardized asset. SCR calculates this rollup from the hazard
damage components it has quantified:

```text
Flood damage returned --------+
Wind damage returned  --------+|
Wildfire damage returned -----++--> adjustedTotalDamage
                                      |
                               future / 2025
                                      |
                                      v
                              overall SCR delta
```

This is an all-available-SCR-hazards rollup, not proof that SCR physically
quantified every hazard. The final delivery must retain a coverage note and must
not describe blank hazard damage fields as zero risk. Hazard-level extraction is
kept for reconciliation and future research, but it is not required in the V1
Parquet grain.

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

The full Solar distribution has now been tested. The leading V2 numerical
candidate is a symmetric arctangent soft-log transform: factors from
`0.333333x` through `3x` remain unchanged; values outside that identity band
approach reciprocal `0.20x` and `5x` bounds. Raw and stabilized fields remain
separate. This is approved for screening/calibration work only; the parameters
still require representative InfraSure EAL/TIV testing before Platform or
client-facing financial use. See the
[factor stabilization experiment](discussions/conus_solar_physical_delta/04_factor_stabilization_experiment.md).

## 4. What this scope is—and is not

### V1 is

- An **asset- and location-specific overall physical-damage change factor**.
- A way to screen the change in an InfraSure asset-level loss metric.
- A baseline-to-future comparison by SCR scenario and horizon.
- A deliberately lightweight alternative to running complete future hazard models.
- A test-first project: determine the dimensions along which SCR's delta actually varies before building a large grid.

### V1 is not

- A rebuild of SCR's climate or hazard models.
- A rerun of the complete InfraSure future hazard-modeling stack.
- A replacement for InfraSure's current expected-loss calculations.
- A reconstruction of SCR's proprietary damage curves.
- A disruption, business-interruption, workability, or combined-value model.
- A hazard-by-hazard EL scaling table in the first delivery.
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

### Current Solar CONUS source status — 2026-08-18

The Solar photovoltaic batch has now arrived earlier than the original staged
sequence anticipated. This changes the order of investigation, not the purpose
or acceptance standard.

```text
InfraSure canonical served grid             SCR Solar workbook drop
13,085 cells                                11,928 unique cells
        \                                      /
         +-- exact shared cell_id contract ---+
                          |
                          v
              1,157 canonical cells absent
                          |
                          v
       preserve raw missing status
       + closest observed donor for complete surface
```

The filename inventory proves that every returned SCR ID is canonical, with no
duplicates, extras, or state-label mismatches. A
17-workbook sample also has exact canonical center coordinates and one common
986-row, 36-column schema. Overall `adjustedTotalDamage` supports a factor in all
17 sampled workbooks; hazard damage is concentrated in Wildfire, Flood, and
Wind, while Heat remains disruption-only.

The full Solar corpus has now produced governed V1 and V2 research Parquets. It
is not an already approved Platform financial factor surface. The raw fields
preserve the 1,157 absent workbooks as explicit missing-source records; the
complete surface uses one closest observed donor per missing cell, with donor
lineage retained. V2 keeps the raw and filled ratios and adds separate
stabilized-candidate fields. See the
[investigation findings](discussions/conus_solar_physical_delta/01_investigation_findings.md)
and [execution plan](plans/SCR%20Solar%20CONUS%20Physical%20Delta%20Parquet%20Plan.md).

The completed full-corpus extraction strengthens the overall-factor case:

- all 11,928 returned workbooks parse successfully;
- every workbook has a nonzero 2025 `adjustedTotalDamage` and a future total at
  every five-year horizon under both scenarios;
- 2035–2040 central factors remain close to `1.0x` for nearly all cells;
- the distribution widens materially toward 2100, especially under SSP5-8.5;
- extreme raw ratios exist and are often associated with very small baseline
  magnitudes, so raw and applied factors must remain separate.

See the [full distribution analysis](discussions/conus_solar_physical_delta/03_full_overall_delta_distribution.md).

## 5. Questions that must be answered before implementation

These questions determine the size and usefulness of the project. The national
Solar files are now available, but they remain investigation evidence until the
controlled logic, full-corpus QA, missingness treatment, and Platform semantics
are approved.

### Question 1 — Does the SCR delta actually vary by location?

This is the largest scope question.

SCR's absolute risk will clearly vary by location. What is not yet proven is whether the **relative baseline-to-future change** also varies materially by location.

```text
Hold constant:
  asset type + asset value + geometry + scenario + horizon

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
        +-- NO  -> Store one overall factor per asset type/scenario/horizon.
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

### Supporting QA — Which hazards contribute to overall physical damage?

The checked-in physical workbook contains eight hazard families and 28 continuous indicators:

```text
Drought       Flood          Heat          Landslide
Subsidence    Precipitation  Wildfire      Wind
```

However, “a hazard appears in the workbook” does not necessarily mean that it
contributes a numeric `adjustedHazardDamage` value to `adjustedTotalDamage`.

The current evidence suggests:

| Hazard family | What is returned | Initial V1 interpretation |
|---|---|---|
| Flood | Inland/coastal depths plus `adjustedHazardDamage` for several sampled asset classes | QA component of overall damage where populated |
| Wind | Wind-speed indicators and a displayed damage function; numeric `adjustedHazardDamage` is sparse in the sample | QA component; tiny denominators can expose factor instability |
| Wildfire | Burn probability, tree cover, FWI, and populated `adjustedHazardDamage` in sampled assets | QA component with broad sampled coverage |
| Heat | Workability and disruption fields; direct structural damage is blank in the sample | Outside V1; retain as reference only |
| Drought | Water stress, duration, and magnitude indicators | Outside direct physical-damage V1 unless SCR later returns damage values |
| Precipitation | Maximum 1-day and 5-day precipitation indicators | Outside direct physical-damage V1; avoid double counting with Flood |
| Landslide | Susceptibility indicator | Outside direct physical-damage V1 |
| Subsidence | Rate indicator | Outside direct physical-damage V1 |
| Hail, tornado, winter weather | Not present in the example | Requires another source or remains explicitly uncovered |

The QA output should therefore classify hazards without expanding the V1
delivery grain:

```text
Hazard present
     |
     +-- Has baseline and future adjustedHazardDamage? --> contributes to QA
     |
     +-- Has only continuous hazard indicator? ----> possible later factor,
     |                                               but outside direct-EL V1
     |
     +-- Not present? ------------------------------> supplementary source or
                                                     clearly not modeled
```

### First live evidence — six-asset portal test (2026-07-21)

The first multi-asset test shows that the overall physical-damage factor must
retain **asset type × location × scenario × horizon**. It does not support one
universal scalar across every asset and location.

The two gas assets are the clearest initial location test. Their Flood physical-damage factor is flat at `1.00x`, while their 2100 Wildfire physical-damage factors differ: Whitehorn is approximately `1.00x` and Frederickson approximately `1.35x`. This is enough to reject a single global physical-damage factor, but not enough to determine the final spatial lookup resolution.

All six assets return the same eight hazard families as indicator/rating records, but numeric physical-damage coverage is much sparser. Therefore, **hazard present is not the same as physical-damage factor available**.

The dashboard may retain disruption, disruption damage equivalent, Heat workability, and combined value for research and reconciliation. V1 must not use those channels to scale InfraSure physical-damage EL.

### Question 3 — Does the delta vary by asset type?

The same location should be tested with at least a solar asset and a wind asset while holding asset value and resilience assumptions constant.

```text
Same location + same physical-damage inputs

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

### Question 8 — Which overall field should drive the V1 delta?

The repository already exposes both:

```text
Overall physical damage
  adjustedTotalDamage

Other overall curves
  adjustedTotalDisruption
  adjustedTotalDisruptionDamageEquivalent
  adjustedTotalValueImpact

Hazard-level curves
  adjustedHazardDamage
  adjustedHazardDisruption
  adjustedHazardDisruptionDamageEquivalent
  adjustedHazardValueImpact
```

The primary V1 calculation is:

```text
Overall physical-damage delta
  = abs(adjustedTotalDamage at future horizon)
    / abs(adjustedTotalDamage at 2025)
```

The agreed V1 use is:

- **`adjustedTotalDamage`:** primary final-delivery input.
- **`adjustedHazardDamage`:** component reconciliation and research only.
- **Disruption, DDE, Heat, and combined-value curves:** research and QA only.
- **Derived magnitude-response curve:** research and QA only unless SCR confirms it represents an official vulnerability relationship.

The example confirms that the overall curve contains multiple components:

```text
adjustedTotalValueImpact
  = adjustedTotalDamage
    + adjustedTotalDisruptionDamageEquivalent
```

At `ssp5-8.5 / 2100` in the example, the total value impact reconciles exactly to those two total components. The hazard rows also explain the composition: Flood and Wildfire contribute quantified value impact, while Heat contributes disruption damage-equivalent even though its hazard value-impact field is blank.

This distinction matters because `adjustedTotalValueImpact` includes disruption
damage equivalent. It is not the overall physical-damage field. The V1 overall
factor must use `adjustedTotalDamage`, not `adjustedTotalValueImpact`.

## 6. The minimum experiment and regional validation

The original decision path used the following two-stage test. The Solar source
drop now covers most of CONUS, so apply the same controlled logic and regional
diagnostics inside that corpus before promoting any national factor table.

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

The regional diagnostics must be completed before the existing Solar corpus is
promoted into a nationwide production factor table. National files being
available is not the same as national methodology approval.

## 7. The four possible architectures

The test result—not an assumption—selects the architecture.

```text
Outcome A: delta does not vary materially by location or asset type

  Delta[asset_type, scenario, horizon]
  -> smallest scope; no spatial lookup required

Outcome B: delta varies by location but not asset type

  Delta[location/cell, scenario, horizon]
  -> spatial lookup; reusable across assets

Outcome C: delta varies by location and asset type

  Delta[location/cell, asset_type, scenario, horizon]
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
| **Utkarsh — SCR fetch owner** | Preserve the submitted Solar configuration and fetch logs and support equivalent Wind/Gas runs after review of the Solar V2 method. No Solar retry is required for the current V1/V2 release. |
| **Data-pipeline owner** | Parse the frozen workbooks, derive raw factors, run spatial/missingness QA, and produce the governed Parquet and variance report. |
| **Divy — model/product decision owner** | Select the initial region and standard asset configurations; approve baseline, decrease-factor, guardrail, hazard-coverage, and Platform presentation decisions. |
| **Prashant / SCR contact — dependency owner** | Close any unresolved SCR input requirements and confirm metric units, baseline semantics, loss-sign convention, inflation treatment, and usage/licensing constraints. |

### What Utkarsh needs to do now

```text
1. Preserve the completed Solar run contract
   -> input template, Solar TICCS class, value/revenue assumptions,
      scenarios, horizons, submitted cell manifest, and fetch logs

2. Preserve the frozen missing-source manifest
   -> 1,157 canonical cells absent; current V1/V2 uses closest observed donors

3. Freeze the final Solar source inventory
   -> do not replace observed files without version/provenance tracking

4. Support controlled comparisons
   -> confirm which prior gas locations/configurations are directly comparable

5. Prepare one next asset-class run only after review
   -> Wind or Gas, using the same immutable inventory and QA pattern
```

Utkarsh should review the Solar method and help reproduce the source pattern for
Wind or Gas. He should not change the stabilization parameters or wire factors
into client-facing EL; those choices remain with Divy's model/product review.

### Phase 0 — Prove the delta

1. Confirm the `adjustedTotalDamage` definition and units.
2. Confirm the baseline and future-period semantics.
3. Confirm that physical-damage values are annualized asset-value impacts.
4. Confirm whether the metric is inflation-neutral and suitable for scaling a current-value InfraSure EL.
5. Run the controlled location/asset/input test matrix.
6. Run the selected state/climate-region batch at the available 25 km x 25 km reference-cell centers.
7. Quantify location, within-region, asset-type, value, geometry, and resilience sensitivity; compare between regions when the test includes more than one.
8. Reconcile `adjustedTotalDamage` to populated hazard-damage components as QA.
9. Review zero/near-zero baselines and the observed delta distribution; propose a baseline floor and any ceiling/floor or soft/log compression only if supported by evidence.
10. Decide whether factors below `1.0` may reduce InfraSure EL or whether the applied underwriting factor has a conservative floor of `1.0`; always retain the raw factor.
11. Select Architecture A, B, C, or D.

### Phase 1 — Implement only the selected dimensions

1. Extend the existing workbook-to-JSON builder into the selected production ingestion path; do not rebuild the proven parser from scratch.
2. Join returned `Output.assetName` through the private manifest to the InfraSure asset ID.
3. Calculate and store the approved overall delta with its baseline, scenario,
   horizon, and necessary asset/location dimensions.
4. Retain the raw SCR workbook and values for reproducibility.
5. Do not build unused grid or asset dimensions.
6. Version the calculation logic and attach every record to its SCR batch run and portfolio/context where applicable.

### Phase 2 — Apply to InfraSure expected loss

1. Retrieve the InfraSure current asset-level loss metric selected for screening.
2. Retrieve the matching overall SCR delta.
3. Calculate the screened future asset-level loss.
4. Preserve current and future values separately.
5. Label the result as an overall SCR physical-damage screen; do not imply
   hazard-level completeness.

```text
current_asset_loss
    x scr_overall_delta_applied(asset/location, scenario, horizon)
    = screened_future_asset_loss
```

### Phase 3 — Present in the Platform

Lead with the overall asset trend. Hazard-level detail may remain available in
research views, but it is not required in the first delivery.

Show:

- Current InfraSure EL.
- Future InfraSure EL.
- Absolute and percentage change.
- Scenario, horizon, asset type, location, and source.
- A clear missing-coverage status.

Do not show:

- An unlabeled SCR percentage beside an InfraSure percentage.
- A tail-risk result derived only from an EL multiplier.
- An uncovered hazard as unchanged.
- A claim that the overall factor represents every individual hazard.

## 9. V1 factor record

Store only the fields needed to reproduce and understand the change:

| Field | Purpose |
|---|---|
| `cell_id` | Exact InfraSure canonical-grid join key |
| `asset_type` | Standardized SCR asset configuration |
| `scenario` | Original SCR scenario |
| `baseline_period` | Exact denominator definition |
| `future_horizon` | Future comparison year/period |
| `scr_metric_name` | Exact source field; V1 is `adjustedTotalDamage` |
| `scr_baseline_value` | Preserved source denominator |
| `scr_future_value` | Preserved source numerator |
| `scr_delta_raw` | Future divided by baseline, preserved without modification |
| `scr_delta_applied` | Raw delta after any approved guardrail; equals raw delta when no guardrail is needed |
| `guardrail_status` | None, capped, compressed, rejected baseline, or manual review |
| `source_product_version` | Reproducibility |
| `raw_record_reference` | Link to the source row/workbook |
| `quality_status` | Approved, provisional, unavailable, or invalid baseline |
| `coverage_status` | Observed workbook, missing source, unavailable total, or invalid baseline |
| `scr_run_id` | Join to the reproducible batch-run directory and manifest |
| `portfolio_id` | InfraSure portfolio context where applicable |
| `created_at` | Factor-record creation timestamp |
| `schema_version` | Version of the factor-calculation and guardrail logic |

The final V1 record is keyed by canonical cell, standardized asset type,
scenario, and horizon. Value, geometry, and resilience belong in the key only
if the experiment proves they affect the overall delta.

## 10. Acceptance criteria

The focused scope is complete when:

1. We know whether SCR's delta varies materially by location, based on both the controlled matrix and a larger state/climate-region batch.
2. We know whether it varies by asset type, value, geometry, or resilience.
3. `adjustedTotalDamage` and the 2025 baseline are documented and validated.
4. Overall damage reconciles to available hazard-damage components within the
   approved tolerance.
5. Hazard-level outputs are retained as QA rather than required delivery rows.
6. Heat disruption and combined value are explicitly excluded from the applied V1 factor.
7. Architecture A, B, C, or D has been selected from evidence.
8. One current-to-future InfraSure physical-damage EL calculation can be reproduced end to end.
9. The observed delta distribution has been reviewed and any ceiling/compression rule is documented; raw and applied deltas remain separate.
10. Tail metrics remain separate unless tail-specific evidence is approved.
11. Licensing permits storing derived deltas and using them in client-facing calculations.
12. The team has measured the error/spread around a climate-region average and decided whether regional averaging, a cell lookup, or per-asset processing is defensible.
13. Zero and near-zero baselines return an explicit status rather than an infinite or arbitrary multiplier.
14. The result is labeled as SCR's overall available physical-damage rollup,
    not proof of complete hazard coverage.
15. Each result is traceable to a run, raw workbook row, schema version, and creation time.

## 11. Recommended decision

Approve the concept as an **SCR-derived, asset- and location-specific overall
physical-damage delta**.

The Solar national grid and numerical V2 candidate now exist. Before detailed
Platform integration, use representative InfraSure assets to answer two primary
questions:

1. Does the stabilized candidate produce defensible EAL/TIV outcomes?
2. Do Wind and Gas require different compression parameters?

Retain the cell-level Solar surface while those tests are conducted. Do not
replace it with regional averages or treat the V2 candidate as a PML/TVaR
adjustment.

The simplest intended product remains:

> SCR tells us how its overall modeled physical damage changes for a standardized
> asset at a particular location. InfraSure uses that relative change as an
> asset-level screening factor without rerunning the full future hazard and
> damage model.

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

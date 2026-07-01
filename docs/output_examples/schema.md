# SCR Returned Output Schema and Interpretation

Status: deep profile from the returned SCR examples plus ClimateMetrics
metadata documents, 2026-07-01.

Local example files:

```text
asset_1232_physical_risks.xlsx
asset_1232_transition_risks.xlsx
```

Metadata source files:

```text
docs/metadata/climatemetrics_metadata.xlsx
docs/metadata/climatemetrics_faq.pdf
docs/metadata/climatemetrics_methodology.pdf
```

The example workbooks and metadata files are checked in for reproducibility.
This markdown file records the useful structure learned from them: how to join
the results back, what each workbook contains, how complete the example data
is, and where the fields can fit into InfraSure.

## Read This First

The returned SCR workbooks are not one-row summaries. They are long-format
model outputs.

The repeated asset fields are context. The analytical data lives across
scenario, horizon, indicator, hazard, and subrisk rows.

ClimateMetrics should be treated as an exposure model-output layer. The
methodology describes physical and transition outputs as exposure metrics and
ratings, not as a direct replacement for InfraSure asset data or a complete
cash-flow forecast.

Most important rule:

```text
Use Output.assetName as the row-level join key.
Do not use SCR assetId as the InfraSure key.
```

Join-back path:

```text
SCR returned workbook
  Output.assetName
      |
      v
scr_manifest.csv.scr_asset_name
      |
      v
scr_manifest.csv.plant_uuid
      |
      v
plants.id
```

`assetId` is useful vendor metadata. In the examples it is `USA_00490`. Store
it, but do not use it as the canonical database identity.

## At a Glance

The two example workbooks cover one uploaded asset:

```text
assetName = is_p_f0d551408183414598a0bd83bf10ee72
assetId   = USA_00490
type      = Gas-Fired Power Generation / IC101020
country   = USA
zone      = Temperate
coords    = (47.079722,-122.365)
```

Observed shapes:

| Output | Rows | Columns | Main analytical axes |
|---|---:|---:|---|
| Physical risk | 952 | 36 | scenario, time horizon, indicator, hazard |
| Transition risk | 240 | 20 | scenario, time horizon, indicator, subrisk |

ASCII shape sketch:

```text
Physical
1 asset
  x 2 scenarios
  x 17 horizons
  x 28 returned physical indicator rows
  = 952 long rows

Transition
1 asset
  x 6 returned scenarios
  x 8 horizons
  x 5 transition indicators
  = 240 long rows
```

Both returned files contain static values only; no worksheet formulas were
found in the workbook XML.

## Metadata-Derived Interpretation Rules

The metadata files change how we should interpret the returned rows:

```text
Asset grain
  One SCR request is one asset analysis.
  Distinct asset types or geographically separated sub-assets should be
  assessed separately, then aggregated at portfolio level.

Geography
  Minimum input is asset centroid coordinates in WGS84.
  Address geocoding is supported, but direct coordinates are preferred.
  Lines and polygons are supported by SCR, but the current exporter sends
  point assets.

Financial inputs
  Asset value supports physical damage quantification.
  Revenue supports transition risk and revenue disruption quantification.
  Scope 1 and Scope 2 are optional; SCR can estimate defaults, but reported
  data improves precision.

Time horizons
  Physical indicators run in 5-year steps from 2025 to 2100.
  Transition indicators run in 5-year steps from 2025 to 2060.
  Indicator values represent a 10-year average centered on the horizon.
  Financial impacts represent the average annual impact from 2025 through the
  selected horizon.

Ratings
  A is best / lowest exposure.
  G is worst / highest exposure.
  Ratings are derived from percentile scores against SCR's reference
  infrastructure universe, anchored to the Expected scenario and 2035 horizon.
```

Implication for InfraSure: keep raw numeric values and SCR letter ratings.
Do not infer cash-flow impacts or insurance outcomes without a product-layer
interpretation step.

## Workbook Anatomy

Both returned workbooks contain the same sheet pattern:

| Sheet | Role | Import stance |
|---|---|---|
| `ReadMe` | Single-asset metadata and SCR field group notes. | Human review only. |
| `Output` | Row-level long-format model output. | Authoritative import source. |

Use the actual `Output` headers. The transition `ReadMe` mentions
`adjustedIndicatorValue`, but that field is not present in the actual
transition `Output` sheet.

## Identity Fields

These fields are repeated on every row and should be used for linkage, audit,
or QA rather than treated as analytical measures.

| Field | Type | Interpretation | Recommended use |
|---|---|---|---|
| `assetName` | text | The generated upload name preserved by SCR. | Primary join to `scr_manifest.csv`. |
| `assetId` | text | SCR's returned asset identifier. | Store as vendor metadata. |
| `reportDate` | date | SCR report/output date. | Versioning and freshness checks. |
| `geolocationCoordinates` | text | SCR-returned coordinate string. | QA against upload; not canonical geospatial identity. |
| `countryCode` | text | ISO3 country code. | QA and filtering. |
| `climateZone` | text | SCR climate-zone label. | Portfolio segmentation. |
| `ticcsSubClass` | text | TICCS subclass code. | Sector/technology grouping and QA. |
| `ticcsSubClassName` | text | Human-readable TICCS subclass. | Display and reporting. |

Import recommendation:

```text
Store repeated asset context once per imported SCR asset.
Store analytical rows separately in long result tables.
```

## Common Analytical Fields

These fields appear in both physical and transition outputs.

| Field | Type | Interpretation | Useful for |
|---|---|---|---|
| `scenario` | text | Scenario family. Physical and transition use different families. | Stress testing and scenario comparisons. |
| `timeHorizon` | text | Historical or future horizon. | Time filters and trend views. |
| `indicator` | text | Driver being measured. | Explaining why a risk score exists. |
| `indicatorUnit` | text | Unit for `indicatorValue`. | Display and QA. |
| `indicatorValue` | numeric | Raw driver value from SCR. | Driver charts and model explainability. |

Keep `timeHorizon` as text in raw import. Physical includes `Historical`;
transition is numeric-looking in this example but should not be assumed to
stay numeric forever.

## Physical Output Profile

File:

```text
asset_1232_physical_risks.xlsx
```

Observed grain:

```text
assetName + scenario + timeHorizon + indicator + hazard
```

The physical output has two climate scenarios:

```text
ssp2-4.5
ssp5-8.5
```

Horizons:

```text
Historical
2025, 2030, 2035, ..., 2100
```

Metadata interpretation:

- `ssp2-4.5` is the moderate/intermediate emissions physical scenario.
- `ssp5-8.5` is the high-emissions, fossil-fuel-intensive physical scenario.
- The methodology maps several transition scenarios back to these two
  physical scenarios when combined climate exposure ratings are produced.
- Physical output is modelled to 2100.
- Indicator values are centered 10-year averages; financial impacts are
  average annual impacts from 2025 to the selected horizon.

Each scenario/horizon combination has 28 rows:

```text
              ssp2-4.5  ssp5-8.5
Historical        28        28
2025              28        28
2030              28        28
...               28        28
2100              28        28
```

Hazard row mix:

```text
Flood          204 | #####-------------------
Heat           204 | #####-------------------
Wind           204 | #####-------------------
Drought        102 | ###---------------------
Wildfire       102 | ###---------------------
Precipitation   68 | ##----------------------
Landslide       34 | #-----------------------
Subsidence      34 | #-----------------------
```

Interpretation:

- Flood, heat, and wind each have 6 indicators.
- Drought and wildfire each have 3 indicators.
- Precipitation has 2 indicators.
- Landslide and subsidence each have 1 indicator.
- The metadata workbook's current `Indicators` sheet lists 27 physical
  indicators and does not list `Subsidence rate`, but the returned workbook
  does include subsidence. The importer should keep returned indicators even
  when metadata mapping is missing, and emit a vocabulary warning.

Indicator families:

```text
Drought
  - Water stress
  - Drought duration
  - Drought magnitude

Flood
  - Fluvial & Pluvial Flood depth - 10 years RP
  - Fluvial & Pluvial Flood depth - 100 years RP
  - Fluvial & Pluvial Flood depth - 500 years RP
  - Coastal flood depth - 10 years RP
  - Coastal flood depth - 100 years RP
  - Coastal flood depth - 500 years RP

Heat
  - Days above 35C
  - Days above 38C
  - Days above 99th percentile
  - WBGT days
  - Heatwave average length
  - Heatwave days

Wind
  - TC wind speed - 10 years RP
  - TC wind speed - 100 years RP
  - TC wind speed - 500 years RP
  - ETS wind speed - 10 years RP
  - ETS wind speed - 100 years RP
  - ETS wind speed - 500 years RP
```

Other physical indicators:

```text
Landslide:     Landslide susceptibility
Precipitation: Max precipitation 1 day, Max precipitation 5 days
Subsidence:    Subsidence rate (returned output; not in current metadata sheet)
Wildfire:      Burn probability, Tree cover, Fire Weather Index (FWI)
```

## Physical Metric Families

Physical output contains three practical metric layers.

```text
indicator layer
  indicatorValue
  indicatorRating

hazard layer
  hazardDamage
  hazardDisruption
  hazardDisruptionDamageEquivalent
  hazardValueImpact
  hazardExposureRating

asset total layer
  totalDamage
  totalDisruption
  totalDisruptionDamageEquivalent
  totalValueImpact
  physicalExposureRating
```

Adjusted versions exist for most physical metrics. Store both adjusted and
unadjusted values. The first product view will likely prefer adjusted values,
but the raw import should not discard either family.

Methodology interpretation:

- `hazardDamage` and `totalDamage` are tied to asset value / replacement
  value. They represent annual expected loss style asset-value impacts.
- `hazardDisruption` and `totalDisruption` are tied to revenue and business
  continuity.
- `hazardDisruptionDamageEquivalent` converts disruption into a
  damage-equivalent form so damage and disruption can be compared or combined.
- Financial impact metrics are available mainly for flood, wind, heat, and
  wildfire. Blank damage/value fields for other hazards can be structurally
  expected.
- Physical exposure ratings are benchmarked A-G ratings, not raw hazard
  intensities.

Physical-specific fields:

| Field | Type | Interpretation | Useful for |
|---|---|---|---|
| `indicatorRating` | text | Rating for the individual indicator. | Driver-level badges. |
| `hazard` | text | Physical hazard group. | Grouping and hazard-level rollups. |
| `HazardRating` | text | Hazard-level rating. Header uses capital `H`. | Raw import and hazard summary. |
| `hazardDamage` | numeric | Hazard impact relative to asset value / replacement value. | Hazard-specific damage screen. |
| `adjustedHazardDamage` | numeric | Adjusted hazard damage. | Preferred damage candidate after validation. |
| `hazardDisruption` | numeric | Hazard impact relative to revenue / business continuity. | Operating-disruption screen. |
| `adjustedHazardDisruption` | numeric | Adjusted disruption. | Preferred disruption candidate after validation. |
| `hazardDisruptionDamageEquivalent` | numeric | Disruption converted to damage-equivalent terms. | Combined impact analysis. |
| `adjustedHazardDisruptionDamageEquivalent` | numeric | Adjusted damage-equivalent disruption. | Combined adjusted impact analysis. |
| `hazardValueImpact` | numeric | Hazard-level value-impact signal. | Ranking hazards within one asset. |
| `adjustedHazardValueImpact` | numeric | Adjusted hazard value-impact signal. | Preferred hazard ranking candidate. |
| `hazardExposureRating` | text | Hazard exposure rating. | Hazard-level display. |
| `adjustedHazardExposureRating` | text | Adjusted hazard exposure rating. | Preferred hazard rating candidate. |
| `totalDamage` | numeric | Asset total damage for the scenario/horizon context. | Asset-level physical rollup. |
| `adjustedTotalDamage` | numeric | Adjusted total damage. | Preferred damage rollup candidate. |
| `totalDisruption` | numeric | Asset total disruption. | Portfolio disruption screening. |
| `adjustedTotalDisruption` | numeric | Adjusted total disruption. | Preferred disruption rollup. |
| `totalDisruptionDamageEquivalent` | numeric | Total disruption converted to damage-equivalent terms. | Combined impact reporting. |
| `adjustedTotalDisruptionDamageEquivalent` | numeric | Adjusted total disruption equivalent. | Preferred combined impact reporting. |
| `totalValueImpact` | numeric | Total asset value-impact signal. | Asset ranking and portfolio rollups. |
| `adjustedTotalValueImpact` | numeric | Adjusted total value-impact signal. | Preferred physical value-impact candidate. |
| `physicalExposureRating` | text | Overall physical exposure rating. | Simple physical badge. |
| `adjustedPhysicalExposureRating` | text | Adjusted overall physical exposure rating. | Preferred physical badge candidate. |

## Physical Completeness and Reliability

Missing values are not automatically errors. Some metrics appear only where
SCR considers the hazard/indicator applicable.

Example coverage:

```text
Asset total metrics:        about 94% populated
Hazard ratings:             about 79% populated
Hazard disruption metrics:  about 50% populated
Hazard damage/value metrics: about 30% populated
Indicator fields:           about 87% populated
```

Practical rule:

```text
If identity fields are present and row axes are present, keep the row.
Treat metric blanks as null model outputs unless a required column is absent.
```

The physical historical rows exist in the matrix, but asset total impact
metrics are blank for those historical rows in this example. For trend charts,
start with future horizons unless SCR confirms a historical impact convention.

Physical rating distribution in the example:

```text
indicatorRating
A   357 | #########---------------
B   156 | ####--------------------
C    61 | ##----------------------
D    50 | #-----------------------
E    38 | #-----------------------
F   239 | ######------------------
NA   51 | #-----------------------

adjustedHazardExposureRating
A   192 | #####-------------------
C   102 | ###---------------------
D   252 | ######------------------
E   102 | ###---------------------
F    24 | #-----------------------
NA  280 | #######-----------------

adjustedPhysicalExposureRating
A   896 | #######################-
NA   56 | #-----------------------
```

The example asset's overall adjusted physical exposure is low (`A`) wherever
the total rating is present, but individual indicators can still have worse
ratings. This is why product UI should show both overall rating and top
drivers.

## Physical ASCII Trend

This trend uses `adjustedTotalValueImpact`, taking one value per
scenario/horizon. The plot is relative within each scenario line.

Horizons shown:

```text
2025 2030 2035 2040 2045 2050 2055 2060 2065 2070 2075 2080 2085 2090 2095 2100
```

ASCII scale:

```text
. low  _  -  ~  =  +  *  # high
```

Example:

```text
ssp2-4.5  .______--~=++**#   min 0.000955   max 0.001023
ssp5-8.5  .....___--~~=+*#   min 0.000953   max 0.001239
```

Interpretation:

- Both scenarios show increasing physical value impact over time.
- `ssp5-8.5` diverges more sharply after mid-century.
- The absolute values are small in this sample, but display scaling still
  needs SCR confirmation before we label them as percentages.

## Physical Usefulness in InfraSure

High-value uses:

- Asset detail: show overall physical rating plus top hazards and indicators.
- Portfolio dashboard: rank assets by worst adjusted physical rating.
- Climate scenario comparison: compare `ssp2-4.5` and `ssp5-8.5`.
- Hazard lens: group exposure by flood, heat, wind, drought, wildfire, etc.
- Diligence workflow: explain which hazard/indicator drives an asset's result.
- QA: compare returned TICCS, coordinates, and country against the upload
  manifest.

Best first product summary:

```text
For each asset + scenario + horizon:
  show adjustedPhysicalExposureRating
  show adjustedTotalValueImpact
  show top N hazards by adjustedHazardValueImpact
  show top N indicators by indicatorRating severity
```

## Transition Output Profile

File:

```text
asset_1232_transition_risks.xlsx
```

Observed grain:

```text
assetName + scenario + timeHorizon + indicator + subrisk
```

Transition scenarios present in the example return:

```text
Below 2C
Current Policies
Delayed Transition
Low Demand
NDCs
Net Zero 2050
```

Metadata scenario universe:

```text
Orderly
  - Net Zero 2050
  - Below 2C

Disorderly
  - Delayed Transition

Too Little, Too Late
  - Fragmented World

Hot House World
  - Nationally Determined Contributions (NDCs)
  - Current Policies

ECI stress extensions
  - Climate Destabilisation
  - Climate Breakdown
```

The importer should accept all eight metadata scenarios. The current returned
example contains six and does not include `Fragmented World`,
`Climate Destabilisation`, or `Climate Breakdown`.

Horizons:

```text
2025, 2030, 2035, 2040, 2045, 2050, 2055, 2060
```

Each scenario/horizon combination has 5 rows:

```text
                     rows per horizon
Below 2C                    5
Current Policies            5
Delayed Transition          5
Low Demand                  5
NDCs                        5
Net Zero 2050               5
```

Subrisk row mix:

```text
Market_demand_shifts   144 | ##############----------
Direct_carbon_cost      96 | ##########--------------
```

Indicator mapping:

```text
Direct_carbon_cost
  - Carbon price
  - scope12_intensity

Market_demand_shifts
  - Revenue growth
  - Inflation
  - scope3_intensity
```

## Transition Metric Families

Transition output has three practical layers.

```text
indicator layer
  indicatorValue

subrisk layer
  subriskRevenueImpact
  subriskExposureRating

asset total layer
  transitionExposureRating
```

Adjusted versions exist for subrisk and asset exposure ratings. Store both.

Methodology interpretation:

- Direct carbon cost measures exposure to Scope 1+2 emissions intensity under
  a carbon-price path. Conceptually it is emissions intensity multiplied by
  carbon price, giving an annual carbon-cost burden relative to revenue.
- Market demand shifts compare an asset/sector revenue path under a climate
  scenario against an inflation-only reference path.
- Scope 3 is estimated by SCR from sector/country inputs, not directly
  uploaded by users in this workflow.
- The Transition Exposure Rating aggregates direct carbon cost and market
  demand shifts into an A-G rating.

Transition-specific fields:

| Field | Type | Interpretation | Useful for |
|---|---|---|---|
| `subrisk` | text | Transition risk driver. | Splitting direct carbon cost and demand-shift effects. |
| `subriskRevenueImpact` | numeric | Revenue-relative impact for the subrisk. | Ranking transition revenue sensitivity. |
| `adjustedSubriskRevenueImpact` | numeric | Adjusted revenue impact for the subrisk. | Preferred subrisk ranking candidate. |
| `subriskExposureRating` | text | Subrisk exposure rating. | Subrisk-level badge/display. |
| `adjustedSubriskExposureRating` | text | Adjusted subrisk exposure rating. | Preferred subrisk rating candidate. |
| `transitionExposureRating` | text | Overall transition exposure rating. | Simple transition badge. |
| `adjustedTransitionExposureRating` | text | Adjusted overall transition exposure rating. | Preferred transition badge candidate. |

## Transition Completeness and Reliability

Example coverage:

```text
Rating fields:       100% populated
Indicator values:     92.5% populated
Subrisk impacts:      87.5% populated
```

The missing subrisk impact rows align with the 2025 baseline rows in this
example. Treat them as null model outputs, not parser failures.

Transition rating distribution in the example:

```text
adjustedSubriskExposureRating
B     3 | ------------------------
C    15 | ##----------------------
D    24 | ##----------------------
E    27 | ###---------------------
F    90 | #########---------------
G    81 | ########----------------

adjustedTransitionExposureRating
B     5 | ------------------------
C    25 | ##----------------------
D    40 | ####--------------------
E    30 | ###---------------------
F    85 | ########----------------
G    55 | ######------------------
```

Unlike the physical example, the transition example has materially worse
ratings. This makes transition output highly useful for ranking assets and
explaining scenario sensitivity.

## Transition ASCII Scenario Stress

This plot uses max `adjustedSubriskRevenueImpact` by scenario and horizon.
The plot is relative within each scenario line.

Horizons shown:

```text
2030 2035 2040 2045 2050 2055 2060
```

ASCII scale:

```text
. low  _  -  ~  =  +  *  # high
```

Example:

```text
Below 2C             +#*=...   min 0.158   max  4.075
Current Policies     ~*#*~..   min 0.241   max  7.423
NDCs                 ~*#*~..   min 0.200   max  6.234
Delayed Transition   .+###*+   min 2.476   max 21.426
Low Demand           =#*=-_.   min 8.407   max 14.720
Net Zero 2050        =#*=-_.   min 13.85   max 22.868
```

Max `adjustedSubriskRevenueImpact` by scenario and subrisk:

| Scenario | Direct carbon cost | Market demand shifts |
|---|---:|---:|
| Below 2C | 0.245 | 4.075 |
| Current Policies | 0.267 | 7.423 |
| Delayed Transition | 21.426 | 2.476 |
| Low Demand | 14.720 | 0.914 |
| NDCs | 0.252 | 6.234 |
| Net Zero 2050 | 22.868 | 0.027 |

Interpretation:

- `Net Zero 2050` and `Delayed Transition` are dominated by direct carbon
  cost for this gas-fired asset.
- `Current Policies`, `NDCs`, and `Below 2C` show larger market-demand-shift
  values than direct-carbon-cost values in this example.
- `Low Demand` shows large direct-carbon-cost values even though its market
  demand shift is low in the example output.

## Transition Usefulness in InfraSure

High-value uses:

- Asset detail: show transition rating by scenario/horizon.
- Portfolio dashboard: rank assets by worst adjusted transition exposure.
- Scenario comparison: expose Current Policies vs Net Zero 2050 vs Delayed
  Transition.
- Financial-risk view: connect `adjustedSubriskRevenueImpact` to revenue
  assumptions from the upload sidecar.
- Technology diagnostics: compare transition sensitivity by TICCS subclass.

Best first product summary:

```text
For each asset + scenario + horizon:
  show adjustedTransitionExposureRating
  show max adjustedSubriskRevenueImpact
  show top subrisk
  show the indicator family behind that subrisk
```

## Rating Semantics

SCR uses A-G ratings across indicator, hazard, physical exposure, transition
exposure, and combined climate exposure concepts.

Confirmed interpretation from the metadata:

```text
A = best / lowest exposure
B
C
D
E
F
G = worst / highest exposure
```

Ratings are derived from continuous 1-100 exposure scores benchmarked against
SCR's reference infrastructure universe. The reference scale is anchored to
the Expected scenario at the 2035 horizon, which is intended to make ratings
comparable over assets, time, sectors, and geographies.

Portfolio-level SCR ratings are computed by mapping letters to numbers,
averaging valid asset ratings, rounding, and mapping back:

```text
A=1, B=2, C=3, D=4, E=5, F=6, G=7
portfolio_rating = letter(round(mean(asset_rating_number)))
```

InfraSure should store the raw letters as strings. If we reproduce SCR-style
portfolio summaries, keep the numeric mapping explicit and preserve the
underlying distribution because a simple average hides dispersion.

## Raw Import Design

Do not write SCR outputs directly into `plants`. Treat SCR as a separate
vendor model-output layer.

Recommended flow:

```text
InfraSure DB assets
  -> SCR upload exporter
  -> SCR upload workbook
  -> SCR processing
  -> returned physical/transition workbooks
  -> output ingestion script
  -> normalized local CSVs
  -> reviewed database tables
  -> product/API views
```

Recommended local outputs before database writes:

```text
scr_output_import_manifest.csv
scr_physical_risk_long.csv
scr_transition_risk_long.csv
scr_output_import_warnings.csv
```

`scr_output_import_manifest.csv`:

```text
import_id
scr_run_id
source_file
output_type
imported_at
row_count
asset_count
matched_asset_count
unmatched_asset_count
warning_count
```

`scr_physical_risk_long.csv` key columns:

```text
import_id
scr_run_id
plant_uuid
portfolio_asset_id
scr_asset_id
scr_asset_name
report_date
scenario
time_horizon
indicator
hazard
```

`scr_transition_risk_long.csv` key columns:

```text
import_id
scr_run_id
plant_uuid
portfolio_asset_id
scr_asset_id
scr_asset_name
report_date
scenario
time_horizon
indicator
subrisk
```

Keep all raw SCR metric columns in the normalized files. Even if the first UI
uses only ratings and top drivers, the full long-format data is valuable for
portfolio analytics and future ontology work.

## Candidate Future Database Tables

| Table | Purpose |
|---|---|
| `scr_import_runs` | One row per imported SCR return package. |
| `scr_import_assets` | One row per SCR asset per import, linked to `plant_uuid` and portfolio context. |
| `scr_physical_risk_results` | Long physical rows keyed by import, plant, scenario, horizon, indicator, and hazard. |
| `scr_transition_risk_results` | Long transition rows keyed by import, plant, scenario, horizon, indicator, and subrisk. |
| `scr_result_warnings` | Import warnings, unmapped vocabularies, and coordinate mismatches. |

This table shape keeps repeat SCR runs auditable and prevents overwriting
older model results.

## Validation Rules for the Ingestion Script

Hard failures:

- Missing `Output` sheet.
- Missing `assetName`.
- `assetName` not found in the matching `scr_manifest.csv`.
- UUID suffix in `assetName` disagrees with manifest `plant_uuid`.
- Physical file has no `hazard` column.
- Transition file has no `subrisk` column.
- Output type cannot be determined from headers.

Warnings:

- `ReadMe.assetName` differs from one or more `Output.assetName` values.
- SCR-returned coordinates differ from upload manifest coordinates.
- `assetId` changes for the same `assetName` across reruns.
- New scenario, hazard, subrisk, or indicator value is not yet in our
  ontology.
- Returned indicator is not present in the current metadata workbook.
- Metadata contains a scenario or indicator that is not present in a returned
  workbook. This is not an error; the return may be a subset.
- Metric fields are blank but identity and row-axis fields are present.
- Expected metric column is missing, but enough columns exist to identify and
  import the result type.

## Product Interpretation Rules

Use these defaults until SCR confirms stronger guidance:

```text
1. Use adjusted ratings/metrics for default UI.
2. Keep unadjusted values available in details or raw export.
3. Do not convert numeric impacts to percentages in storage.
4. Do not rank by indicatorValue alone; it has mixed units.
5. Rank physical hazard drivers by adjustedHazardValueImpact when populated.
6. Rank transition drivers by adjustedSubriskRevenueImpact when populated.
7. Treat A as lowest exposure and G as highest exposure.
8. Store rating letters as categorical strings; only map to numbers in an
   explicit portfolio-scoring routine.
```

## Ontology Candidates

The returned outputs provide useful controlled vocabulary seeds:

```text
scenario
timeHorizon
hazard
subrisk
indicator
indicatorUnit
rating values
ticcsSubClass
climateZone
```

Do not immediately rename vendor vocabularies in raw import. Instead:

```text
raw SCR value -> ontology mapping table -> product display label
```

This protects auditability and gives us room to normalize names later.

## Open Questions

- Which adjusted metric should become the default physical ranking metric?
- What display scaling should SCR numeric impact fields use?
- Should we expose SCR outputs to clients directly, or only derived
  InfraSure summaries?
- Should reruns replace the active view while preserving history, or should
  users choose a run explicitly?
- Should physical and transition imports be accepted separately, or only as a
  paired return package from the same upload run?

# SCR Returned Output Schema and Usage Notes

Status: draft schema interpretation from the two returned SCR examples,
2026-07-01.

Example files:

```text
asset_1232_physical_risks.xlsx
asset_1232_transition_risks.xlsx
```

This document describes what the returned SCR workbooks contain, how to join
them back to InfraSure data, and where the result can be useful in the product
and database workflow.

## Core Decision

The returned workbooks preserve the uploaded `assetName` exactly. That makes
`assetName` the bridge back to InfraSure:

```text
SCR Output.assetName
  -> scr_manifest.csv.scr_asset_name
  -> scr_manifest.csv.plant_uuid
  -> plants.id
```

`assetId` is SCR's identifier, for example `USA_00490`. Store it, but do not
use it as the InfraSure database key.

The matching `scr_manifest.csv` from the upload run is required for a clean
import because it carries context SCR does not return:

- `plant_uuid`
- `portfolio_asset_id`
- workspace and portfolio identifiers
- source type: reference vs tenant / greenfield
- upload validation warnings
- asset value and revenue source
- run ID and generated timestamp

If the manifest is missing, `plant_uuid` can be reconstructed from names like
`is_p_f0d551408183414598a0bd83bf10ee72`, but that loses portfolio and run
context.

## Workbook Shape

Both output examples contain:

| Sheet | Purpose | Ingestion stance |
|---|---|---|
| `ReadMe` | Asset metadata and field groups. | Useful for quick human review. Do not use as the row-level source of truth. |
| `Output` | Long-format risk rows. | Authoritative sheet for import. |

Both returned files contain static values only; no worksheet formulas were
found in the workbook XML.

The ingestion script should always read actual `Output` headers. The
transition `ReadMe` mentions `adjustedIndicatorValue`, but that column is not
present in the current transition `Output` sheet.

## Common Fields

These fields appear in both physical and transition outputs.

| Field | Type | Meaning | Useful for |
|---|---|---|---|
| `assetId` | text | SCR's returned asset identifier. | Vendor audit, support tickets, cross-checking repeated SCR exports. |
| `assetName` | text | The InfraSure-generated upload name that SCR preserved. | Primary join key back to `scr_manifest.csv`. |
| `reportDate` | date | Date SCR produced or labeled the result. | Versioning, freshness, comparing reruns. |
| `geolocationCoordinates` | text | SCR-returned coordinate string, such as `(47.079722,-122.365)`. | Audit only; prefer InfraSure DB coordinates for canonical geospatial joins. |
| `countryCode` | text | ISO3 country code, usually `USA`. | QA and filtering. |
| `climateZone` | text | SCR climate-zone classification. | Portfolio segmentation, climate-zone rollups. |
| `ticcsSubClass` | text | SCR/TICCS subclass code from the upload mapping. | Technology/sector grouping and QA. |
| `ticcsSubClassName` | text | Human-readable TICCS subclass name. | Display and reporting. |
| `scenario` | text | Scenario name. Physical and transition use different scenario families. | Scenario analysis, stress comparisons. |
| `timeHorizon` | text | Historical/future horizon. Keep as text because physical includes `Historical`. | Time-series comparison and horizon filters. |
| `indicator` | text | Climate or transition indicator name. | Explaining which driver produced a risk result. |
| `indicatorUnit` | text | Unit for `indicatorValue`. | Display and QA. |
| `indicatorValue` | numeric | Raw indicator value returned by SCR. | Driver-level analysis, charts, explanations. |

Recommended import behavior:

- Keep the original field names in the first normalized CSVs.
- Convert to internal `snake_case` only when designing database tables.
- Preserve `timeHorizon` as text initially.
- Preserve `assetId` and `assetName` even after joining to `plant_uuid`.
- Do not join by coordinates, display names, country, or TICCS fields.

## Physical Risk Output

File:

```text
asset_1232_physical_risks.xlsx
```

Observed shape:

- `Output`: 36 columns
- data rows: 952
- row grain:

```text
assetName + scenario + timeHorizon + indicator + hazard
```

Example scenario values:

```text
ssp2-4.5
ssp5-8.5
```

Example hazards:

```text
Drought
Flood
Heat
Landslide
Subsidence
```

Physical-specific fields:

| Field | Type | Meaning | Useful for |
|---|---|---|---|
| `indicatorRating` | text | SCR rating for the indicator. | Driver-level color/rating displays. |
| `hazard` | text | Physical hazard group. | Grouping results into drought/flood/heat/etc. |
| `HazardRating` | text | SCR hazard-level rating. Header currently uses capital `H`. | Hazard summary tables. |
| `hazardDamage` | numeric | Hazard-level asset value / capex impact. | Estimating value-at-risk style signals by hazard. |
| `adjustedHazardDamage` | numeric | Adjusted hazard damage output. | Main adjusted hazard damage metric, if we decide adjusted is preferred. |
| `hazardDisruption` | numeric | Hazard-level revenue / opex disruption impact. | Operating disruption screening. |
| `adjustedHazardDisruption` | numeric | Adjusted disruption output. | Main adjusted disruption metric, if adjusted is preferred. |
| `hazardDisruptionDamageEquivalent` | numeric | Disruption translated to damage-equivalent terms. | Combining disruption and damage into a comparable impact view. |
| `adjustedHazardDisruptionDamageEquivalent` | numeric | Adjusted damage-equivalent disruption. | Adjusted combined risk analysis. |
| `hazardValueImpact` | numeric | Hazard-level total value-impact signal. | Ranking hazards within an asset. |
| `adjustedHazardValueImpact` | numeric | Adjusted hazard value-impact signal. | Preferred hazard ranking candidate after validation. |
| `hazardExposureRating` | text | SCR hazard exposure rating. | Hazard-level rating display. |
| `adjustedHazardExposureRating` | text | Adjusted hazard exposure rating. | Adjusted hazard-level rating display. |
| `totalDamage` | numeric | Asset-level total damage across physical hazards for the row context. | Asset-level physical loss rollup. |
| `adjustedTotalDamage` | numeric | Adjusted total damage. | Preferred total damage candidate after validation. |
| `totalDisruption` | numeric | Asset-level total disruption. | Portfolio disruption screening. |
| `adjustedTotalDisruption` | numeric | Adjusted total disruption. | Preferred total disruption candidate after validation. |
| `totalDisruptionDamageEquivalent` | numeric | Total disruption converted to damage-equivalent terms. | Combined physical impact reporting. |
| `adjustedTotalDisruptionDamageEquivalent` | numeric | Adjusted total disruption damage equivalent. | Adjusted combined physical impact reporting. |
| `totalValueImpact` | numeric | Total value-impact signal. | Asset ranking and portfolio rollups. |
| `adjustedTotalValueImpact` | numeric | Adjusted total value-impact signal. | Preferred ranking candidate after validation. |
| `physicalExposureRating` | text | Overall physical exposure rating. | Simple physical risk badge. |
| `adjustedPhysicalExposureRating` | text | Adjusted overall physical exposure rating. | Preferred physical risk badge after validation. |

Potential product uses:

- Plant detail: show top physical hazards by `adjustedHazardValueImpact`.
- Portfolio view: rank assets by worst `adjustedPhysicalExposureRating`.
- Scenario view: compare `ssp2-4.5` vs `ssp5-8.5` across horizons.
- Diligence workflow: flag assets with high flood, heat, drought, or
  wildfire-related exposure.
- Data QA: compare SCR `ticcsSubClassName`, coordinates, and country against
  what we uploaded.

Implementation cautions:

- The numeric impact fields look like fractional values. Do not multiply or
  relabel them as percentages until we confirm SCR's display convention.
- Store both adjusted and unadjusted values. Decide which to show at the
  product layer.
- Preserve `HazardRating` exactly in raw files, but normalize to
  `hazard_rating` in database tables.

## Transition Risk Output

File:

```text
asset_1232_transition_risks.xlsx
```

Observed shape:

- `Output`: 20 columns
- data rows: 240
- row grain:

```text
assetName + scenario + timeHorizon + indicator + subrisk
```

Example scenario values:

```text
Below 2°C
Current Policies
NDCs
Delayed Transition
Net Zero 2050
```

Example subrisk values:

```text
Direct_carbon_cost
Market_demand_shifts
```

Transition-specific fields:

| Field | Type | Meaning | Useful for |
|---|---|---|---|
| `subrisk` | text | Transition subrisk driver. | Splitting direct carbon cost vs market-demand impacts. |
| `subriskRevenueImpact` | numeric | Revenue impact for the subrisk. | Ranking transition-risk revenue sensitivity. |
| `adjustedSubriskRevenueImpact` | numeric | Adjusted revenue impact for the subrisk. | Preferred subrisk ranking candidate after validation. |
| `subriskExposureRating` | text | SCR rating for the subrisk. | Subrisk-level badge/display. |
| `adjustedSubriskExposureRating` | text | Adjusted subrisk exposure rating. | Preferred adjusted subrisk display. |
| `transitionExposureRating` | text | Overall transition exposure rating. | Simple transition risk badge. |
| `adjustedTransitionExposureRating` | text | Adjusted overall transition exposure rating. | Preferred transition risk badge after validation. |

Potential product uses:

- Plant detail: show transition exposure under each climate/economic scenario.
- Portfolio view: rank assets by `adjustedTransitionExposureRating`.
- Scenario comparison: compare Current Policies vs Net Zero 2050 / Below 2C.
- Financial-risk view: connect `subriskRevenueImpact` to revenue assumptions
  from the SCR upload sidecar.
- Asset-type diagnostics: compare transition risk across TICCS subclasses.

Implementation cautions:

- Do not assume transition `timeHorizon` is always numeric in future files;
  store it as text first.
- Store `subriskRevenueImpact` as a raw numeric value and decide display
  scaling later.
- Trust the actual `Output` headers over the `ReadMe` field list.

## Fit in InfraSure Workflow

The SCR result data fits as a vendor model-output layer. It should not replace
the canonical asset table; it should attach to assets through `plant_uuid` and
portfolio context from the manifest.

Recommended flow:

```text
DB assets
  -> SCR upload exporter
  -> scr_upload.xlsx
  -> SCR processing
  -> SCR returned workbooks
  -> SCR output ingestion
  -> normalized local CSVs
  -> reviewed database tables
  -> product/API views
```

Useful downstream surfaces:

| Surface | Useful fields |
|---|---|
| Asset detail page | Overall physical/transition ratings, top hazards, top subrisks, scenario/horizon trend. |
| Portfolio dashboard | Worst assets by adjusted ratings, count of high-risk assets, hazard concentration by geography. |
| Client export | Joined asset identity, SCR ratings, scenario/horizon metrics, source run metadata. |
| Data quality review | SCR-returned `assetId`, coordinates, TICCS class, country, and manifest validation warnings. |
| Ontology work | `hazard`, `subrisk`, `indicator`, `scenario`, and `timeHorizon` become candidate controlled vocabularies. |

## Proposed Local Normalized Outputs

Before writing to the database, create local normalized files beside the
returned workbooks.

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

Keep all SCR metric columns in those files, even if the first UI only uses a
few ratings. The raw long-format data is valuable for later scenario and
portfolio analytics.

## Future Database Shape

Do not write directly into existing `plants` records. Treat SCR as a separate
vendor result dimension.

Candidate future tables:

| Table | Purpose |
|---|---|
| `scr_import_runs` | One row per imported SCR return package. |
| `scr_import_assets` | One row per SCR asset per import, including `assetId`, `assetName`, `plant_uuid`, and portfolio context. |
| `scr_physical_risk_results` | Long physical rows keyed by import, plant, scenario, horizon, indicator, and hazard. |
| `scr_transition_risk_results` | Long transition rows keyed by import, plant, scenario, horizon, indicator, and subrisk. |

This keeps repeat runs auditable and avoids overwriting older SCR results.

## Validation Rules for the Ingestion Script

Hard failures:

- Missing `Output` sheet.
- Missing `assetName`.
- `assetName` not found in `scr_manifest.csv`.
- UUID suffix in `assetName` disagrees with manifest `plant_uuid`.
- Physical file missing `hazard`.
- Transition file missing `subrisk`.

Warnings:

- Unknown `assetId` for an otherwise matched `assetName`.
- SCR-returned coordinates differ from upload manifest coordinates.
- `ReadMe.assetName` differs from one or more `Output.assetName` values.
- Expected metric column missing, but enough columns exist to identify the
  result type.
- New scenario, hazard, subrisk, or indicator value not yet in our ontology.

## Open Questions

- Should adjusted metrics be the default product view, with unadjusted values
  available in detail?
- What display scaling should we use for numeric impact fields?
- Should SCR scenario/hazard/subrisk names be kept verbatim or mapped to an
  internal ontology immediately?
- What retention policy should we use for repeated SCR reruns of the same
  portfolio?
- Which outputs can be shown to clients under SCR's distribution terms?

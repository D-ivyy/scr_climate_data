# ClimateMetrics Metadata Reference

Status: source map and implementation notes, 2026-07-01.

This folder contains SCR / ClimateMetrics reference material used to interpret
the returned physical and transition output workbooks.

## Files

```text
climatemetrics_metadata.xlsx
climatemetrics_faq.pdf
climatemetrics_methodology.pdf
```

Use these files as interpretation support. The returned `Output` sheets remain
the source of truth for row-level ingestion.

## Workbook Contents

`climatemetrics_metadata.xlsx` contains these useful sheets:

| Sheet | Useful content |
|---|---|
| `Indicators` | Current physical indicator vocabulary: hazard, sub-hazard, type, unit, description. |
| `Scenarios` | Physical scenario descriptions for `SSP2-4.5` and `SSP5-8.5`. |
| `Time horizons` | Physical horizon rule: 2025-2100 in 5-year steps. |
| `CIR thresholds` | Climate Indicator Rating threshold table. |
| `Indicators TR` | Transition subrisk and indicator vocabulary. |
| `Scenarios TR` | Transition scenario categories and physical-scenario mapping. |
| `Time horizons TR` | Transition horizon rule: 2025-2060 in 5-year steps. |

The workbook also contains placeholder separator sheets and an older indicator
sheet. The current `Indicators` and `Indicators TR` sheets are the practical
ones for importer vocabulary mapping.

## Key Implementation Rules

Identity:

```text
Output.assetName -> scr_manifest.csv.scr_asset_name -> plant_uuid -> plants.id
```

Do not use SCR `assetId` as the InfraSure key.

Asset grain:

```text
One SCR request = one asset analysis.
Distinct asset types or materially separate sub-assets should be split before
SCR upload, then aggregated later at portfolio level.
```

Geography:

```text
Minimum input: WGS84 centroid coordinates.
Preferred input: precise coordinates or geometry.
Supported by SCR but not yet by exporter: point + buffer, line, polygon.
```

Financial inputs:

```text
asset_value -> physical damage / replacement-value impact
revenue     -> transition risk and physical disruption impact
scope_1/2   -> optional transition precision improvement
```

The methodology says at least one of asset value or revenue is required for
the financial-information category, but our upload tests should still prefer
providing both when available because different modules use different inputs.

## Time Horizon Semantics

Physical:

```text
2025 to 2100
5-year steps
indicator values = 10-year average centered on the horizon
financial impacts = average annual impacts from 2025 to the horizon
```

Transition:

```text
2025 to 2060
5-year steps
indicator values = 10-year average centered on the horizon
financial impacts = average annual impacts from 2025 to the horizon
```

## Scenario Maps

Physical scenarios:

| Scenario | Interpretation |
|---|---|
| `SSP2-4.5` | Moderate/intermediate emissions scenario. |
| `SSP5-8.5` | High-emissions, fossil-fuel-intensive scenario. |

Transition scenario universe:

| Category | Scenario | CMS physical mapping |
|---|---|---|
| Orderly | Net Zero 2050 | SSP2-4.5 |
| Orderly | Below 2C | SSP2-4.5 |
| Disorderly | Delayed Transition | SSP2-4.5 |
| Too Little, Too Late | Fragmented World | SSP2-4.5 |
| Hot House World | Nationally Determined Contributions (NDCs) | SSP2-4.5 |
| Hot House World | Current Policies | SSP2-4.5 |
| ECI | Climate Destabilisation | SSP5-8.5 |
| ECI | Climate Breakdown | SSP5-8.5 |

The returned transition example currently contains six scenarios. It does not
include `Fragmented World`, `Climate Destabilisation`, or `Climate Breakdown`.
The importer should support all eight.

## Physical Indicator Vocabulary

The current workbook metadata lists 27 physical indicators:

```text
Flood:          6 indicators
Wind:           6 indicators
Heat:           6 indicators
Drought:        3 indicators
Wildfire:       3 indicators
Precipitation:  2 indicators
Landslide:      1 indicator
```

The returned physical example contains 28 rows per scenario/horizon because it
also includes `Subsidence rate`. That term is not present in the current
metadata workbook. Import behavior should be:

```text
keep returned row
mark metadata_mapping_status = missing
emit vocabulary warning
```

## Transition Indicator Vocabulary

Transition indicators are grouped under two subrisks:

```text
Direct Carbon Cost
  - Scope 1+2 Emissions Intensity
  - Carbon Price

Market Demand Shifts
  - Average Annual Inflation
  - Average Annual Revenue Growth
  - Scope 3 Emissions Intensity
```

The returned output uses machine-like labels:

```text
Direct_carbon_cost
Market_demand_shifts
scope12_intensity
scope3_intensity
```

Keep raw SCR labels in normalized imports and map to display labels through an
ontology table.

## Rating Semantics

Confirmed rating direction:

```text
A = best / lowest exposure
G = worst / highest exposure
```

Ratings are derived from 1-100 percentile-style exposure scores against SCR's
reference infrastructure universe, anchored to the Expected scenario at the
2035 horizon.

Portfolio rating rule from the methodology:

```text
A=1, B=2, C=3, D=4, E=5, F=6, G=7
portfolio_rating = letter(round(mean(valid_asset_rating_numbers)))
```

Store raw letters. Only convert to numbers inside an explicit scoring or
portfolio aggregation routine.

## Methodology Implications

Physical:

- Damage metrics are expressed relative to asset value / replacement value.
- Disruption metrics are expressed relative to revenue / business continuity.
- Financial impact metrics are mainly available for flood, wind, heat, and
  wildfire.
- Blank metric values can be structurally valid when a hazard is not
  financially quantified.

Transition:

- Direct carbon cost is driven by Scope 1+2 emissions intensity and carbon
  price.
- Market demand shifts compare revenue trajectory against inflation/reference
  growth.
- Scope 3 is estimated by SCR from sector/country inputs in this workflow.

Limitations:

- Tipping points and cascading system dynamics are not explicitly modelled.
- Physical supply-chain dependencies are not modelled.
- Data Quality Score is discussed in the FAQ/methodology but is not present
  in the current returned output examples.

## Use in InfraSure

Use metadata for:

- schema validation
- scenario and indicator ontology
- display labels
- rating semantics
- documentation of assumptions and limitations

Do not use metadata to reject a valid returned row. Returned workbooks can
include values not yet listed in the metadata package.

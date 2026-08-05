# SCR gas 146-location validation report

- **Reference run:** Gas-fired power generation
- **SCR report date:** 2026-08-04
- **Validation date:** 2026-08-05
- **Status:** Evidence for team review; not yet approval for a full CONUS run

## Executive Summary

- **The submitted locations are the grid centers.** All 146 SCR asset coordinates match the `lat_center` and `lon_center` of their selected cells in the 13,085-cell, 0.25° CONUS reference grid. Cell ID, state, and ISO/RTO labels also match 146/146.
- **An overall physical-damage change factor is calculable for every tested gas location.** `adjustedTotalDamage` has a nonzero 2025 baseline and a future value for all 146 locations under both SSP2-4.5 and SSP5-8.5. The factor is derived by InfraSure; SCR returns the underlying damage values, not a separate change-factor column.
- **The overall factor is complete because the available hazard damage fields collectively cover this sample.** At baseline, Wildfire has damage for 145 locations and Flood for 33; their union covers all 146. The overall result does not mean that SCR quantified physical damage for every returned hazard.
- **Hazard-specific physical-damage factors remain sparse.** Wildfire supports a factor for 145/146 locations and Flood for 33/146. Wind has a few 2100 damage values but no 2025 denominator. Heat returns disruption rather than physical damage. Drought, Earthquake, Landslide, Precipitation, and Subsidence return indicators/ratings but no physical-damage values in this gas sample.

The practical conclusion is to treat the overall gas physical-damage factor as a valid experimental output for all 146 sampled locations, while retaining hazard-specific factors only where both baseline and future damage exist. The next comparison should repeat these same locations for Photovoltaic and Onshore Wind before deciding whether to run all 13,085 cells.

## What was tested

```text
13,085-cell 0.25° CONUS reference grid
                    |
                    | select 146 cell IDs
                    v
       exact lat_center / lon_center
                    |
                    | create one standardized gas asset per location
                    v
     146 SCR CSV + 146 SCR XLSX exports
                    |
        +-----------+-------------+
        |                         |
        v                         v
 overall asset damage       hazard-level damage
 adjustedTotalDamage        adjustedHazardDamage
        |                         |
        v                         v
 146/146 valid factors      Flood 33 / Wildfire 145
```

The source archive contains 146 CSV/XLSX pairs representing 146 unique cells. Every CSV has 986 rows and the same 36-column schema. Every workbook uses:

| Input | Value |
| --- | --- |
| Asset type | Gas power plant |
| TICCS subclass | `IC101020` — Gas-Fired Power Generation |
| Asset value | $10,000,000 |
| Annual revenue | $1,000,000 |
| Scenarios | SSP2-4.5 and SSP5-8.5 |
| Horizons | Historical and 2025–2100 in five-year steps |
| Returned hazards | 9 |

This consistency is important: location changes across the sample, while asset type, asset value, and revenue remain fixed.

## Answers to the validation questions

| Question | Test | Result | Interpretation |
| --- | --- | --- | --- |
| Were cell centers used? | Join SCR cell IDs and coordinates to the reference grid | 146/146 exact coordinate matches | Yes. This is a center-point experiment. |
| Are the files unique? | Count cell IDs and file pairs | 146 unique cells; no duplicate cell IDs; 146 CSV/XLSX pairs | No duplicate location was detected. |
| Is the schema consistent? | Compare CSV columns and row counts | One 36-column schema; every CSV has 986 rows | The batch can be processed with one parser. |
| Is the overall physical-damage field present? | Check `adjustedTotalDamage` at 2025, 2050, and 2100 | 146/146 for both scenarios and every tested horizon | Overall physical-damage factors are calculable for all sampled cells. |
| Is the baseline usable? | Check missing and zero 2025 total damage | 146/146 nonblank and nonzero | No denominator is missing for the overall factor. |
| Does total damage reconcile? | Sum distinct `adjustedHazardDamage` values by asset, scenario, and horizon | 876/876 groups match within `1e-12` | `adjustedTotalDamage` is the sum of the available hazard physical-damage components in this sample. |
| Does every hazard have damage? | Compare hazard presence with populated damage fields | No | Hazard indicators/ratings are much more complete than financial damage conversion. |
| Can Wind produce a factor? | Require Wind damage at 2025 and a future horizon | 0/146 | A few 2100 values exist, but no baseline exists; do not calculate a Wind factor. |
| Is Heat physical damage? | Check Heat damage and disruption fields | No Heat physical damage; disruption is populated | Heat must not enter the V1 physical-damage factor as a hazard-damage result. |
| Did adaptation change the values? | Compare each populated raw field with its adjusted counterpart | No mismatches in this batch | No adaptation effect is observable here; this is not a universal rule for future exports. |

## Definition of the factor

SCR returns annualized damage values as negative impacts. For communication, the factor should use their magnitudes:

```text
Overall gas physical-damage factor(asset, scenario, future horizon)

                    abs(adjustedTotalDamage at future horizon)
              =     ------------------------------------------
                    abs(adjustedTotalDamage at 2025 baseline)
```

Because the baseline and projected values have the same negative sign, the direct ratio gives the same positive factor. Store the baseline, future value, and raw factor together; never store only the ratio.

Interpretation:

| Factor | Meaning |
| ---: | --- |
| `< 1.00x` | SCR's modeled annualized physical damage is lower than the 2025 baseline. |
| `1.00x` | No modeled change at SCR's returned precision. |
| `> 1.00x` | SCR's modeled annualized physical damage is higher than the 2025 baseline. |

The factor is a relative change in SCR's modeled damage output. It is not itself a dollar loss, and it is not yet validated as a direct multiplier for InfraSure expected loss.

## Overall gas physical-damage results

All four scenario/horizon comparisons have 146 valid factors:

| Scenario | Horizon | Valid | Below 1x | Equal 1x | Above 1x | Minimum | Median | Maximum |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| SSP2-4.5 | 2050 | 146 | 16 | 68 | 62 | 0.942x | 1.000x | 1.217x |
| SSP2-4.5 | 2100 | 146 | 13 | 65 | 68 | 0.880x | 1.000x | 1.719x |
| SSP5-8.5 | 2050 | 146 | 12 | 68 | 66 | 0.924x | 1.000x | 1.242x |
| SSP5-8.5 | 2100 | 146 | 10 | 57 | 79 | 0.830x | 1.008x | 1.911x |

The factors do vary by location, especially by 2100, but much of the sample remains close to `1.00x`. This rejects the idea that one universal number describes every location, while also suggesting that a large share of grid cells may have little modeled change for a gas asset.

### Examples

**Higher result:** `Cell_374078_FL_Non-ISO_FRCC`, SSP5-8.5 / 2100.

```text
2025 adjustedTotalDamage = -0.0058335
2100 adjustedTotalDamage = -0.0111470

factor = 0.0111470 / 0.0058335 = 1.9109x
```

**Lower result:** `Cell_339424_TX_ERCOT`, SSP5-8.5 / 2100.

```text
2025 adjustedTotalDamage = -0.0003577
2100 adjustedTotalDamage = -0.0002971

factor = 0.0002971 / 0.0003577 = 0.8304x
```

The lower result is not an error by itself. Climate-model variability, hazard interaction, or the vendor's annualized calculation can produce a future value below the selected baseline. These cases should be flagged for review rather than automatically forced above `1.00x`.

## What contributes to overall damage

The total is complete across locations, but the contributing hazards are not complete across the nine returned hazard families.

At 2025 and 2050 under both scenarios:

```text
113 cells: Wildfire only
 32 cells: Flood + Wildfire
  1 cell : Flood only
---------------------------
146 cells: some physical damage contributor exists
```

At 2100, Wind damage also appears in a small number of totals:

| Scenario | Flood damage populated | Wildfire damage populated | Wind damage populated |
| --- | ---: | ---: | ---: |
| SSP2-4.5 / 2100 | 33 | 145 | 10 |
| SSP5-8.5 / 2100 | 33 | 145 | 2 |

Therefore:

```text
overall damage coverage = 146/146

does not mean

every hazard has a damage model at every location
```

The all-location coverage occurs because Flood and Wildfire collectively cover every cell in this selected sample. It should not be assumed in advance for all 13,085 grid cells or for another asset type.

## Hazard-level availability

| Hazard | Files containing hazard rows | Numeric indicator value | Any physical damage | Valid 2025-to-future factor | V1 treatment |
| --- | ---: | ---: | ---: | ---: | --- |
| Wildfire | 146 | 146 | 145 | 145 | Primary hazard-specific factor where present |
| Flood | 146 | 32 | 33 | 33 | Primary hazard-specific factor where present |
| Wind | 146 | 146 | 10 | 0 | Preserve; unavailable as a change factor because the 2025 denominator is missing |
| Heat | 146 | 146 | 0 | 0 | Disruption research only; not physical damage |
| Drought | 146 | 146 | 0 | 0 | Indicator/rating only in this sample |
| Earthquake | 146 | 140 | 0 | 0 | Indicator/rating only in this sample |
| Landslide | 146 | 146 | 0 | 0 | Indicator/rating only in this sample |
| Precipitation | 146 | 146 | 0 | 0 | Indicator/rating only in this sample |
| Subsidence | 146 | 143 | 0 | 0 | Indicator/rating only in this sample |

“No damage” in this table means that the financial damage field is blank. It must not be converted to zero physical risk.

### Hazard-factor ranges where calculable

| Hazard | Scenario / horizon | Valid | Median | Minimum | Maximum | Main caution |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| Flood | SSP2-4.5 / 2050 | 33 | 1.018x | 0.876x | 1.987x | Small sample; location-specific |
| Flood | SSP2-4.5 / 2100 | 33 | 1.043x | 0.707x | 17.560x | Extreme ratios can arise from tiny baselines |
| Flood | SSP5-8.5 / 2050 | 33 | 1.026x | 0.810x | 2.248x | Small sample; location-specific |
| Flood | SSP5-8.5 / 2100 | 33 | 1.086x | 0.521x | 36.535x | Requires denominator and absolute-change guardrails |
| Wildfire | SSP2-4.5 / 2050 | 145 | 1.000x | 0.994x | 1.060x | Many exactly flat values |
| Wildfire | SSP2-4.5 / 2100 | 145 | 1.000x | 0.996x | 1.185x | Many exactly flat values |
| Wildfire | SSP5-8.5 / 2050 | 145 | 1.000x | 1.000x | 1.132x | Many exactly flat values |
| Wildfire | SSP5-8.5 / 2100 | 145 | 1.000x | 1.000x | 1.778x | Change is concentrated in a subset of cells |

This is why an eventual production scalar may require a ceiling, logarithmic compression, or another guardrail. No transformation should be selected yet. First retain and inspect the raw baseline, future damage, absolute change, and factor distribution across multiple asset types.

## Damage is not combined value impact

The primary candidate for the physical-damage experiment is:

```text
adjustedTotalDamage
```

Do not substitute:

```text
adjustedTotalValueImpact
  = adjustedTotalDamage
    + adjustedTotalDisruptionDamageEquivalent
```

The combined value field includes SCR's disruption damage-equivalent. In this gas sample, disruption factors can become extremely large when baseline disruption is tiny. Those ratios are not suitable as physical-damage climate-change factors.

The report therefore keeps three concepts separate:

| Concept | Field | Current InfraSure use |
| --- | --- | --- |
| Overall physical damage | `adjustedTotalDamage` | Primary all-hazard experimental factor |
| Hazard physical damage | `adjustedHazardDamage` | Primary hazard-specific factor where valid |
| Combined damage plus disruption equivalent | `adjustedTotalValueImpact` | Research and reconciliation only |

## Quality and interpretation caveats

1. **The sample is standardized, not a real portfolio.** Each location uses the same gas classification, $10 million asset value, and $1 million revenue.
2. **A 0.25° cell is only approximately 25 km.** Its physical width varies by latitude.
3. **Center-point output does not describe within-cell variation.** The test assigns the grid-cell center as a point asset.
4. **Overall coverage may not generalize.** All 146 gas locations are covered because Flood and Wildfire overlap; another asset type or untested cell may lack a physical-damage denominator.
5. **A missing hazard result is not zero risk.** It means a usable physical-damage value was not returned.
6. **Ratios can mislead when the baseline is tiny.** Every derived record should retain the baseline magnitude and absolute movement, and flag near-zero denominators.
7. **Factors below 1x should remain visible.** They need review, not automatic truncation.
8. **No adaptation effect is observable in this batch.** Raw and adjusted values match wherever both are populated; future files still require this check.
9. **SCR usage rights must be reviewed.** The workbook disclaimer restricts redistribution; keep raw exports and detailed derived material internal unless permission is confirmed.

## Recommended next step

Use this gas run as the reference implementation. Ask Utkarsh to repeat the same 146 cell centers for:

1. Photovoltaic generation — TICCS `IC702010`.
2. Onshore wind — TICCS `IC701010`.

Hold the location set, asset value, revenue, scenarios, horizons, and export format constant. Then compare coverage and factors by asset class.

```text
same 146 locations
        |
        +---- Gas reference     complete
        +---- Photovoltaic      Utkarsh replication
        +---- Onshore Wind      Utkarsh replication
        |
        v
asset-type comparison and QA gate
        |
        v
team decision on 13,085-cell full run
```

The 13,085-cell × 3-asset run should begin only after the team confirms:

- whether the overall physical-damage factor is the primary InfraSure output;
- whether hazard-specific factors remain supporting outputs;
- how to treat factors below `1.00x`;
- the near-zero-baseline rule and any ceiling/compression experiment;
- SCR extraction limits, licensing, storage, and runtime expectations.

## Reproducibility

The checked evidence is preserved as:

- `docs/extra/physical_risk_data.zip` — original 146-location gas export archive.
- `docs/scr_profile/validation/2026-08-05_gas_146_location_manifest.csv` — the exact cell IDs and coordinates for replication.
- `docs/scr_profile/validation/2026-08-05_gas_146_validation_metrics.json` — machine-readable validation results.
- `scripts/validate_gas_location_sample.py` — standard-library validator that rebuilds the metrics and manifest from the raw archive.

Run from the repository root:

```bash
python3 scripts/validate_gas_location_sample.py \
  --zip docs/extra/physical_risk_data.zip \
  --grid /path/to/hazard_conus_grid_dev_common_benchmark_grid_served_conus_cell_ids_v2026_06.csv \
  --output docs/scr_profile/validation/2026-08-05_gas_146_validation_metrics.json \
  --manifest-output docs/scr_profile/validation/2026-08-05_gas_146_location_manifest.csv
```

The reference grid is an external input. The report records the 146/146 match result, while the generated manifest preserves the exact submitted coordinates so the Solar PV and Onshore Wind replications do not depend on rediscovering the locations.

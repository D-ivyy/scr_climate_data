---
author: InfraSure
created: 2026-09-22
updated: 2026-09-22
status: owner-approved experimental annual-revenue proxy; production financial application not approved
---

# SCR transition-risk financial application framework

## Executive answer

SCR already provides the two transition-risk impact outputs:

1. `Direct Carbon Cost` impact; and
2. `Market Demand Shifts` impact.

Carbon price, Scope 1+2 intensity, revenue growth, and Scope 3 intensity are
model inputs or explanatory indicators. They are **not additional percentages
to add to the two impacts**.

```text
Carbon price ($/tCO2) + Scope 1+2 intensity (tCO2/M$)
                              |
                              v
             Direct Carbon Cost impact + rating

Revenue growth (%) + Scope 3 intensity (tCO2/M$)
                              |
                              v
             Market Demand Shifts impact + rating
```

The embedded SCR ReadMe declares both numeric subrisk impacts as annualized
percentages of asset revenue / OpEx. That establishes the source-declared unit,
but not yet the precise denominator, scale, sign convention, time convention,
or combination rule required for an InfraSure financial calculation.

Until those semantics are confirmed, InfraSure should preserve the source
values and ratings and must not present them as validated cash-flow impacts.
For the local trial, the owner has approved treating both source values as
percentage-point adjustments to annual V6 revenue, separately and additively,
with the proxy assumption visible in every derived field and dashboard view.

## Inputs, outputs, and ratings are different field types

| Layer | Field | Source unit | Correct role |
|---|---|---:|---|
| Input indicator | Carbon price | `$/tCO2` | Economic pathway assumption used in Direct Carbon Cost |
| Input indicator | Scope 1+2 emissions intensity | `tCO2/M$` | Asset/sector emissions exposure used in Direct Carbon Cost |
| Input indicator | Revenue growth | `%` | Economic pathway assumption used in Market Demand Shifts |
| Input indicator | Scope 3 emissions intensity | `tCO2/M$` | Value-chain exposure used in Market Demand Shifts |
| Model output | Direct Carbon Cost impact | source-declared `%` | Candidate operating-cost or financial stress |
| Model output | Market Demand Shifts impact | source-declared `%` | Candidate revenue stress or uplift |
| Screening output | Direct Carbon Cost rating | `A-G` | Categorical severity band, not another numeric impact |
| Screening output | Market Demand Shifts rating | `A-G` | Categorical severity band, not another numeric impact |
| Screening output | Overall transition rating | `A-G` | SCR's overall categorical result; not a numeric sum or average |

The numeric impacts and ratings answer different questions:

```text
Impact value -> How large and in which direction is the modeled effect?
Rating       -> Into which SCR screening band does the result fall?
```

The rating should therefore travel with the impact, but should not be converted
into a percentage or multiplied into revenue.

## Do not apply the explanatory indicators a second time

### Direct Carbon Cost

Do not independently calculate a production Direct Carbon Cost by multiplying
carbon price by Scope 1+2 intensity and then also apply SCR's Direct Carbon Cost
impact. That would risk double counting the same modeled channel and would omit
any undocumented SCR adjustments.

Actual Wind Template B example, `Expected`, 2030:

```text
Carbon price                  19.969 $/tCO2
Scope 1+2 intensity           3.265740 tCO2/M$
                               |
                               v
SCR Direct Carbon Cost impact -0.001872  [source-declared %]
SCR Direct Carbon Cost rating A
```

Multiplying the two indicators produces an intermediate dimensional result,
not the published SCR impact:

```text
19.969 $/tCO2 x 3.265740 tCO2/M$
= approximately 65.21 $/M$
```

That intermediate value does not reproduce `-0.001872`. It therefore cannot be
used as a substitute for the published SCR impact and suggests that the export
uses additional model logic, scaling, sign treatment, or adjustment that is not
documented in the current workbook.

### Market Demand Shifts

Do not add Scope 3 intensity to revenue growth or to the Market Demand impact.
The units are incompatible:

```text
Revenue growth       = 0.630592 %
Scope 3 intensity    = 1.371611 tCO2/M$
```

Adding these numbers would be dimensionally invalid. SCR presents them as the
indicators associated with its Market Demand Shifts output, but the current
export does not disclose the exact formula:

```text
SCR Market Demand Shifts impact = 2.045696 [source-declared %]
SCR Market Demand Shifts rating = D
```

If the source semantics are validated, `2.045696` is the candidate percentage
to apply. Scope 3 should remain available for explanation and audit, not be
applied a second time.

## TIV is not the correct default denominator

Total insured value (TIV) is a stock measure of the asset's physical or
replacement value. Revenue and OpEx are annual flow measures.

```text
TIV       -> physical asset value at risk
Revenue   -> annual income flow
OpEx      -> annual operating-cost flow
Cash flow -> annual revenue minus costs and other obligations
```

SCR's embedded definition describes transition impacts as annualized effects on
asset revenue / OpEx. It does not currently establish that either impact is a
percentage of TIV. Applying an annual revenue or cost percentage directly to TIV
would mix a flow percentage with a stock value and could materially overstate
the result.

Therefore:

```text
Physical damage ratio x TIV                 -> potentially valid physical loss
Transition impact x TIV                     -> not supported by current evidence
Market Demand impact x annual revenue       -> candidate, pending validation
Direct Carbon Cost impact x annual OpEx      -> candidate, pending validation
```

The `assetValue` field in a workbook or import template does not, by itself,
prove that TIV is the denominator of the exported transition impacts.

## Owner-approved trial financial application

### Common annual-revenue proxy

For the trial, interpret the source values as percentage points and use annual
V6 revenue as the common proxy base:

```text
direct_factor = 1 + direct_carbon_cost_impact / 100
market_factor = 1 + market_demand_impact / 100
overall_factor = 1 + (direct_carbon_cost_impact + market_demand_impact) / 100

direct_revenue_proxy = baseline_revenue x direct_factor
market_revenue_screen = baseline_revenue x market_factor
overall_revenue_screen = baseline_revenue x overall_factor
```

For actual Wind `cell 267458 · MN`, baseline V6 annual revenue is
`$2,234,525.14` for the standardized 100 MW project. With Direct Carbon Cost
`-0.001872` and Market Demand Shifts `+2.045696`:

```text
direct_factor = 0.99998128x
market_factor = 1.02045696x
overall_factor = 1.02043824x

direct_revenue_delta = approximately -$41.83
market_revenue_delta = approximately +$45,711.59
overall_revenue_delta = approximately +$45,669.76
overall_revenue_screen = approximately $2,280,194.90
```

This is an owner-approved scenario-screening proxy, not a validated forecast.
Direct Carbon Cost may ultimately require an OpEx denominator; the trial does
not claim that annual revenue is its correct production denominator.

### Two-channel cash-flow screening

The more financially coherent treatment keeps revenue and operating-cost
channels separate:

```text
market_delta = annual_revenue x market_demand_impact / 100

carbon_delta = confirmed_DCC_denominator x direct_carbon_cost_impact / 100

stressed_cash_flow = baseline_cash_flow + market_delta + carbon_delta
```

This is a deliberately separate future workflow, not a reason to delay the
current annual-revenue screening package:

```text
Current governed screening workflow
  Direct Carbon impact x annual revenue proxy
  Market Demand impact x annual revenue
  -> available now; explicitly labelled as screening

Future cash-flow workflow
  Direct Carbon impact x governed OpEx denominator
  Market Demand impact x governed annual revenue
  -> combine through a cash-flow model after OpEx is available
```

The current package must preserve the Direct Carbon source impact and factor so
the future workflow can replace only the financial denominator. SCR does not
need to be re-extracted, and the current annual-revenue proxy must not be
silently relabelled as an OpEx result.

The sign should be carried exactly as SCR defines it. InfraSure should not
invert the Direct Carbon Cost sign until SCR confirms whether a negative value
means an adverse financial impact or whether the field represents a cost-rate
increase using the opposite convention.

### Additive overall transition screening factor

The trial displays a same-base combined factor as an explicitly experimental
screen:

```text
combined_impact = market_demand_impact + direct_carbon_cost_impact

combined_factor = 1 + combined_impact / 100
```

Using the Wind example:

```text
Market Demand Shifts impact  +2.045696
Direct Carbon Cost impact    -0.001872
                              ---------
Combined source value         2.043824
Experimental factor           1.02043824x
```

This calculation assumes both impacts are additive percentages of the same
annual-revenue base. That is an owner-approved trial convention, not an SCR
methodology conclusion, so it must not overwrite InfraSure's governed revenue
or cash-flow metrics.

The numeric `overall_transition_screening_factor` is an InfraSure-derived trial
field. It is separate from SCR's supplied `overallTransitionRating` A-G field.

## What the current full-corpus evidence establishes

- Both numeric subrisk impacts carry a source-declared `%` unit in SCR's
  embedded ReadMe.
- The same ReadMe describes a `0-1` range, while exported impacts range from
  approximately `-0.947056` to `37.002403`. The scale conflict is unresolved.
- Raw and adjusted impacts are identical for all non-null Solar and Wind
  observations in the current corpus.
- Solar has one identical transition profile across all observed cells.
- Wind has two exact economic profiles separated at a contiguous asset-ID
  boundary; the reason for the boundary is not yet confirmed.
- The Market Demand impact varies by scenario, horizon, asset profile, and Wind
  source regime, but not meaningfully by geography within a regime.
- Structural source blanks should remain null and must not be spatially filled.

## Physical damage and transition risk must remain separate

| Dimension | Physical damage | Transition risk |
|---|---|---|
| Question | How does climate change alter hazard-driven physical loss? | How might policy and market transition affect revenue or costs? |
| Scenarios | `ssp2-4.5`, `ssp5-8.5` | Nine policy/economic pathways |
| Horizons | 2025-2100, five-year steps | 2025-2050, five-year steps |
| Primary output | Damage level and change factor | Two financial impacts plus ratings |
| Candidate base | Physical EAL or, for a validated damage ratio, TIV | Annual revenue, OpEx, or cash flow |
| Current InfraSure use | Stabilized physical EAL adjustment | Research and screening only |

Transition impacts must not use the physical-damage ratio logic, physical
factor compression, or a physical TIV denominator without separate evidence.

## Proposed recipient fields

Until the semantics are validated, retain both source evidence and application
status:

```text
cell_id
asset_type
scenario
horizon
carbon_price
carbon_price_unit
scope_1_2_intensity
scope_1_2_intensity_unit
revenue_growth
revenue_growth_unit
scope_3_intensity
scope_3_intensity_unit
direct_carbon_cost_impact_raw
direct_carbon_cost_impact_adjusted
direct_carbon_cost_source_unit
direct_carbon_cost_rating
market_demand_impact_raw
market_demand_impact_adjusted
market_demand_source_unit
market_demand_rating
overall_transition_rating
source_regime
financial_application_status
```

Recommended initial status:

```text
financial_application_status = pending_semantic_validation
```

## Required validation questions

The following questions must be resolved before production multiplication:

1. Does `2.045696` mean exactly `2.045696%`, rather than a fractional or indexed
   value?
2. Is Market Demand Shifts always measured against annual revenue?
3. Is Direct Carbon Cost measured against OpEx, revenue, or another denominator?
4. What does the sign of each subrisk impact mean?
5. Can the two subrisk impacts be combined, and if so, under what denominator
   and mathematical rule?
6. Why are raw and adjusted impacts identical in the current Solar and Wind
   exports?
7. Why does Wind switch between two exact economic profiles at one asset-ID
   boundary?

The horizon semantics are no longer treated as an open question for this
package. SCR documentation states that transition indicator values are 10-year
averages centered on the selected horizon, while the financial impacts are
average annual impacts from 2025 through that horizon. They are not cumulative
dollar totals and should not be labelled as a point-in-time impact.

## Current decision

InfraSure may parse, package, display, compare, and join the transition fields
to its grid-cell revenue layer. For the local trial it may calculate and show:

```text
Direct Carbon annual-revenue proxy
Market Demand annual-revenue screen
Additive overall transition annual-revenue screen
```

Each view must preserve the raw source values, source-declared unit, proxy-base
assumption, calculation method, and research status. InfraSure should not yet:

- apply either transition impact to TIV;
- add Scope 3 intensity to Market Demand impact;
- recalculate Direct Carbon Cost from Carbon Price and Scope 1+2 and then also
  apply SCR's published impact;
- promote the additive combination into a governed cash-flow factor; or
- overwrite baseline revenue, OpEx, cash flow, physical EAL, or physical-loss
  metrics.

## Evidence

- Current full-corpus semantics and source-regime findings:
  [`03_transition_sample_semantics_and_regime_findings.md`](03_transition_sample_semantics_and_regime_findings.md)
- Reproducible compact sample:
  [`transition_compact_sample.csv`](../../../../notebooks/transition_risk/outputs/2026-09-22/transition_compact_sample.csv)
- Transition notebook workflow:
  [`notebooks/transition_risk/README.md`](../../../../notebooks/transition_risk/README.md)

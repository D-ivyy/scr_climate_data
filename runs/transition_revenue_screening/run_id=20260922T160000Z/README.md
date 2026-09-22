# SCR transition revenue screening trial

Run ID: `20260922T160000Z`
Status: research source run; not a production cash-flow forecast

## Coverage

- Rows: `1,413,180`
- Grain: `cell_id x asset_type x scenario x horizon`
- Assets: Solar and Wind Farm
- Scenarios: `9`
- Horizons: `6` (`2025`, `2030`, `2035`, `2040`, `2045`, `2050`)

## Operational interpretation

- SCR operational field: `adjustedSubriskRevenueImpact`; the raw field is retained for audit.
- Impact scale: interpreted as percentage points.
- Sign: positive is an annual-revenue uplift; negative is an annual-revenue drag.
- Direct Carbon Cost: temporarily applied to annual revenue as a disclosed screening proxy pending a governed OpEx denominator.
- Market Demand Shift: applied to annual revenue.
- Overall screen: `1 + (direct_carbon_adjusted + market_demand_adjusted) / 100`, with both impacts applied additively to the same revenue base.
- TIV: never used.
- Outliers: no clipping, compression, winsorization, or other transform is applied.
- Missing SCR or revenue values: retained as unavailable, never replaced with zero or `1.0x`.

## Horizon meaning

- Indicator values are 10-year averages centered on the selected horizon.
- Financial impacts are average annual impacts from 2025 through the selected horizon.
- A horizon value is not a cumulative dollar total and is not a point-in-time-only impact.

The numeric overall factor is an InfraSure screening calculation, not SCR's A-G overall transition rating.
See `manifest.json` for pinned inputs and assumptions and `qa_report.json` for validation results.

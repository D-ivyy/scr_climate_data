# SCR Local Dashboard

Local browser dashboard for exploring SCR returned physical and transition
output. It is intentionally static: no npm install, no framework, and no
external charting CDN.

## Build Data

From the repo root:

```bash
python scripts/build_dashboard_data.py \
  --physical docs/output_examples/asset_1232_physical_risks.xlsx \
  --transition docs/output_examples/asset_1232_transition_risks.xlsx \
  --out dashboard/data/example_asset_1232.json
```

Optional private join-back fields can be added with:

```bash
python scripts/build_dashboard_data.py \
  --physical docs/output_examples/asset_1232_physical_risks.xlsx \
  --transition docs/output_examples/asset_1232_transition_risks.xlsx \
  --manifest runs/<run_id>/scr_manifest.csv \
  --out dashboard/data/example_asset_1232.json
```

Only commit returned SCR files or generated dashboard JSON when the data is
safe to publish.

## Run Locally

```bash
python -m http.server 8765
```

Open:

```text
http://localhost:8765/dashboard/
```

Opening `index.html` directly is not recommended because browsers usually
block local JSON loading from `file://` pages.

## Dashboard Data Model

The builder writes:

- `meta`: source files, generated timestamp, row counts, missing fields.
- `assets`: SCR identity fields and optional manifest join-back fields.
- `physical.trends`: scenario/horizon physical trend values.
- `physical.hazards`: hazard ranking values with worst indicators.
- `physical.indicators`: row-level physical indicator values and ratings.
- `transition.scenario_rankings`: peak scenario and subrisk ranking.
- `transition.trends`: scenario/horizon transition trend values.
- `transition.subrisks`: row-level transition subrisk values and ratings.

## Interpretation Notes

- The dashboard uses SCR `assetName` as the join key, matching the manifest
  guidance in the output schema docs.
- Physical impact fields are stored as raw SCR values, but the dashboard
  defaults to a percent-style readability view. Use the `Impact display`
  control to switch between percent-style, basis points, and raw values.
- Percent-style and basis-point displays are simple transformations of the raw
  value. They are not confirmed SCR product-facing unit labels.
- Physical values are best read as exposure-model outputs, not final insurance
  or cash-flow impacts.
- Hazard rows distinguish quantified impact from severity. `not quantified`
  means SCR did not return a numeric hazard value impact for that hazard in the
  selected scenario/horizon.
- Transition values are useful for ranking scenarios and separating direct
  carbon cost from market-demand shifts.
- Numeric impact fields remain raw SCR model-output values until SCR confirms
  product-facing units.

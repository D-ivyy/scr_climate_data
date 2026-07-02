# Task Context: SCR Climate Data Dashboard and Output Analysis

Date: 2026-07-02
Area: scr-climate-data
Task: dashboard-analysis

## Objective

Build and document a local SCR ClimateMetrics workflow that can generate SCR upload files, inspect returned physical and transition workbooks, and make the returned outputs understandable through a local dashboard.

The core product question was: after SCR returns physical and transition results, can we trace the asset back to InfraSure and explain what the returned numbers mean without misleading ourselves about units, ratings, or model semantics?

## Background

SCR requires a bulk-upload file for asset analysis and returns physical and transition Excel workbooks. The InfraSure workflow needs:

- a stable upload asset identifier that can map back to `plant_uuid` or tenant asset identity,
- a compact upload file that SCR accepts,
- a clear schema for returned workbooks,
- a dashboard that makes one returned asset readable before designing platform ingestion.

The work started in `.lab/scr_climate_data` inside the platform repo and was then promoted into the standalone public repo:

```text
/Users/divy/code/personal/renewablesinfo/scr_climate_data
git@github.com:D-ivyy/scr_climate_data.git
```

## Problems Encountered

1. **Upload identity needed a reliable join-back path**
   - SCR returns `assetName` and `assetId`.
   - We decided `assetName` should carry our generated internal stable key and map back through `scr_manifest.csv`.
   - `assetId` is SCR/vendor metadata, not the InfraSure canonical key.

2. **Template-derived output initially risked carrying unnecessary workbook sheets**
   - SCR accepted a compact workbook style.
   - The workflow now separates upload output from manifest/reject diagnostics.

3. **Returned SCR values were hard to interpret**
   - Physical impact values are very small raw numbers.
   - We added raw, percent-style, and basis-point display modes, while keeping the caveat that SCR has not confirmed the final product-facing unit labels.

4. **Transition output was easy to oversimplify**
   - Direct carbon cost is not a CSV-selected default. It is one returned transition subrisk.
   - The returned transition workbook also includes market-demand-shift rows.

5. **Hazard output mixed hazard-level impacts with long indicator rows**
   - Initial display put long indicator labels directly into the hazard ranking row.
   - This made the row hard to scan, so the dashboard now uses expandable hazard rows.

6. **Damage curves needed careful interpretation**
   - SCR returns hazard-level damage/disruption/value metrics and row-level indicator magnitudes.
   - It does not return an explicit official damage function with magnitude on x and damage on y.
   - The dashboard now labels magnitude-response plots as derived exploratory views, not confirmed vendor vulnerability curves.

## What We Fixed

1. **Created the standalone SCR repo workflow**
   - Repository initialized and pushed to `D-ivyy/scr_climate_data`.
   - Public-repo handling kept generated private upload/workbook/run outputs controlled.

2. **Added upload/export workflow**
   - `scripts/export_scr_upload.py` generates SCR-compatible upload output.
   - Run outputs include upload, manifest, and reject diagnostics.

3. **Documented SCR input/output concepts**
   - `docs/guide.md`
   - `docs/metadata/README.md`
   - `docs/output_examples/schema.md`
   - `docs/output_examples/README.md`

4. **Added dashboard data builder**
   - `scripts/build_dashboard_data.py` reads the returned physical and transition Excel `Output` sheets and writes normalized JSON.
   - It validates required output sheets/columns and preserves important raw SCR fields.

5. **Added local dashboard**
   - `dashboard/index.html`
   - `dashboard/assets/app.js`
   - `dashboard/assets/styles.css`
   - `dashboard/data/example_asset_1232.json`

6. **Improved dashboard interpretability**
   - Physical trend metric toggle:
     - `adjustedTotalValueImpact`
     - `adjustedTotalDisruption`
   - Physical display toggle:
     - percent-style
     - basis points
     - raw SCR value
   - Transition driver selector:
     - all drivers
     - direct carbon cost
     - market demand shifts
   - Context `View` buttons on KPI cards and major sections.
   - Expandable hazard rows with indicator details.
   - Returned hazard curves for damage/disruption/value fields.
   - Derived magnitude-response plots where indicator magnitudes vary.

7. **Verified important data facts**
   - Physical returned rows: `952`.
   - Transition returned rows: `240`.
   - One returned sample asset: `is_p_f0d551408183414598a0bd83bf10ee72`.
   - Flood `adjustedHazardValueImpact` is flat in the raw workbook across both scenarios and all future horizons.
   - Hazard-level Excel-to-JSON parity checks passed for representative rows.

## Files Touched

### Created Or Significantly Added

- `dashboard/index.html`
- `dashboard/assets/app.js`
- `dashboard/assets/styles.css`
- `dashboard/data/example_asset_1232.json`
- `dashboard/README.md`
- `scripts/build_dashboard_data.py`
- `scripts/export_scr_upload.py`
- `docs/guide.md`
- `docs/metadata/README.md`
- `docs/output_examples/schema.md`
- `docs/output_examples/README.md`
- `docs/extra/tasks_history/2026-07-02__scr-climate-data__dashboard-analysis/`

### Source / Example Data Used

- `docs/Climate_Metrics_Import_tempate.xlsx`
- `docs/output_examples/asset_1232_physical_risks.xlsx`
- `docs/output_examples/asset_1232_transition_risks.xlsx`
- `docs/metadata/climatemetrics_metadata.xlsx`
- `docs/metadata/climatemetrics_faq.pdf`
- `docs/metadata/climatemetrics_methodology.pdf`

### Local Noise

- `docs/.DS_Store` remains ignored local noise.

## Current Status

- [x] Public SCR repo exists and is pushed.
- [x] Local dashboard runs from `http://localhost:8765/dashboard/`.
- [x] Returned physical and transition examples are normalized to dashboard JSON.
- [x] Physical and transition schema docs explain fields and interpretation.
- [x] Dashboard includes contextual help and driver/metric controls.
- [x] Dashboard exposes hazard-level curves and derived magnitude-response plots.
- [x] Verification commands passed after the latest changes.
- [ ] Vendor-facing units for impact fields still need confirmation from SCR.
- [ ] Magnitude-response plots need product wording review before any client-facing use.
- [ ] Database ingestion tables are not implemented yet.

## Next Steps

1. Get SCR/vendor confirmation on:
   - final unit labels for value impact, disruption, and revenue impact,
   - A-G benchmark population,
   - whether magnitude-response interpretation is acceptable.
2. Add importer design for returned workbooks:
   - asset context table,
   - physical trend table,
   - physical hazard table,
   - physical indicator table,
   - transition trend/subrisk table.
3. Connect private `scr_manifest.csv` to InfraSure plant/tenant records.
4. Add portfolio-level dashboard support once more returned SCR examples are available.
5. Decide which dashboard views should become platform UI components versus lab-only analysis tooling.

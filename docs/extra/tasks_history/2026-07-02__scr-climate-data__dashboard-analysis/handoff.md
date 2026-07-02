# Handoff: SCR Climate Data Dashboard and Output Analysis

## 10-Bullet Summary

1. The SCR workflow now lives in the standalone repo `D-ivyy/scr_climate_data`.
2. The upload/export side uses generated SCR asset names plus a private manifest for InfraSure join-back.
3. Returned physical and transition SCR workbooks are documented in `docs/output_examples/schema.md`.
4. The local dashboard runs at `http://localhost:8765/dashboard/`.
5. `scripts/build_dashboard_data.py` converts returned Excel `Output` sheets into `dashboard/data/example_asset_1232.json`.
6. Physical dashboard views include value impact, disruption, hazard ranking, indicator detail, returned hazard curves, and derived magnitude-response plots.
7. Transition dashboard views include scenario ranking, direct-carbon-cost vs market-demand filtering, trend lines, and subrisk driver tables.
8. Context `View` buttons explain ratings, metrics, caveats, join keys, and methodology assumptions.
9. Flood impact being flat is in the raw SCR workbook, not a dashboard bug.
10. Magnitude-response plots are derived from returned rows and must not be described as official SCR vulnerability/damage functions without vendor confirmation.

## Files Touched

Core dashboard:

```text
dashboard/index.html
dashboard/assets/app.js
dashboard/assets/styles.css
dashboard/data/example_asset_1232.json
dashboard/README.md
```

Scripts:

```text
scripts/build_dashboard_data.py
scripts/export_scr_upload.py
```

Docs:

```text
docs/guide.md
docs/metadata/README.md
docs/output_examples/README.md
docs/output_examples/schema.md
docs/extra/tasks_history/2026-07-02__scr-climate-data__dashboard-analysis/
```

Example and metadata files:

```text
docs/Climate_Metrics_Import_tempate.xlsx
docs/output_examples/asset_1232_physical_risks.xlsx
docs/output_examples/asset_1232_transition_risks.xlsx
docs/metadata/climatemetrics_metadata.xlsx
docs/metadata/climatemetrics_faq.pdf
docs/metadata/climatemetrics_methodology.pdf
```

## Repro Commands

From repo root:

```bash
cd /Users/divy/code/personal/renewablesinfo/scr_climate_data
```

Rebuild dashboard JSON:

```bash
/usr/bin/python3 scripts/build_dashboard_data.py \
  --physical docs/output_examples/asset_1232_physical_risks.xlsx \
  --transition docs/output_examples/asset_1232_transition_risks.xlsx \
  --out dashboard/data/example_asset_1232.json
```

Run local dashboard:

```bash
python -m http.server 8765
```

Open:

```text
http://localhost:8765/dashboard/
```

Verify:

```bash
node --check dashboard/assets/app.js
/usr/bin/python3 -m py_compile scripts/build_dashboard_data.py
git diff --check
curl -sSf http://localhost:8765/dashboard/ >/tmp/scr_dashboard_index_check.html
```

## Next Action Roadmap

### Phase A: Vendor Semantics Confirmation

Read first:

```text
docs/metadata/README.md
docs/output_examples/schema.md
dashboard/README.md
```

Ask SCR to confirm:

- exact unit labels for `adjustedTotalValueImpact`,
- exact unit labels for `adjustedTotalDisruption`,
- exact unit labels for `adjustedSubriskRevenueImpact`,
- meaning and benchmark population for A-G ratings,
- whether magnitude-response plots are acceptable derived interpretations.

### Phase B: Add Ingestion Design

Read first:

```text
scripts/build_dashboard_data.py
docs/output_examples/schema.md
docs/guide.md
```

Design tables for:

- SCR run metadata,
- asset context,
- physical trend rows,
- physical hazard rows,
- physical indicator rows,
- transition trend rows,
- transition subrisk rows,
- manifest join-back fields.

Critical gotcha:

```text
Output.assetName is the join key.
SCR assetId is vendor metadata.
```

### Phase C: Expand Beyond One Example Asset

Needed:

- more returned physical workbooks,
- more returned transition workbooks,
- private manifests for those uploads.

Tasks:

- build multiple JSON datasets,
- test dashboard asset selector with more than one asset,
- validate whether flat flood behavior is asset-specific or common.

### Phase D: Product UI Planning

Candidate platform views:

- asset-level physical exposure summary,
- top hazard drivers,
- physical value/disruption trend toggle,
- transition scenario ranking,
- direct carbon cost vs market demand split,
- portfolio rollup and distribution views.

Keep lab-only unless validated:

- magnitude-response plots,
- raw indicator-level curve interpretation,
- any UI copy implying financial loss units are final.

## Critical Caveats

- Percent-style and basis-point displays are dashboard readability transforms.
- Magnitude-response plots are derived, not vendor-confirmed damage functions.
- Physical disruption and transition revenue impact are separate workbook concepts.
- Some hazards have ratings but no quantified hazard value impact.
- Some hazards have disruption but no damage, especially Heat in the sample.

## Current Git State At Handoff

Last pushed functional commit before these task docs:

```text
b380c84 Add hazard magnitude response plots
```

Expected ignored local noise:

```text
docs/.DS_Store
```

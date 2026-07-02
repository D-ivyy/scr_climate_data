# SCR Climate Data

Utilities and documentation for exporting InfraSure asset rows into SCR's
climate-data upload format, then joining SCR's returned physical and
transition risk outputs back to InfraSure assets.

## Repository Scope

This repo contains:

- `scripts/export_scr_upload.py`: dev/prod DB to SCR upload exporter
- `scripts/build_dashboard_data.py`: returned SCR workbooks to dashboard JSON
- `dashboard/`: local static dashboard for exploring returned SCR output
- `docs/`: upload, manifest, output-schema, and ingestion notes
- `docs/Climate_Metrics_Import_tempate.xlsx`: SCR upload template used by
  the exporter
- `docs/output_examples/`: returned SCR physical/transition examples and
  interpretation notes
- `docs/metadata/`: ClimateMetrics metadata workbook, FAQ, methodology, and
  source interpretation notes
- `runs/`: checked-in example run artifacts

Database credentials remain local-only:

```text
.env
```

## What SCR Outputs Help Answer

The returned physical and transition files are useful because they let us ask
product-level questions after joining SCR `assetName` back through the private
manifest:

- Which assets have the worst physical exposure?
- Which hazards drive the exposure?
- How does exposure change from 2025 to 2100?
- Which scenario is worse for a plant?
- Is transition risk mostly carbon-cost driven or market-demand driven?
- How do assets compare inside a portfolio?
- What should we show on an asset detail page or client risk report?

The detailed question-to-field mapping is in
[`docs/output_examples/schema.md`](docs/output_examples/schema.md#questions-this-output-answers).

## Setup

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Fill `.env` with the appropriate database URL. The exporter reads
`DATABASE_URL_DEV` by default.

## Run

```bash
python scripts/export_scr_upload.py \
  --workspace-slug demo \
  --portfolio-name "Q3 Outlook"
```

The default template path is:

```text
docs/Climate_Metrics_Import_tempate.xlsx
```

You can override it:

```bash
python scripts/export_scr_upload.py \
  --workspace-slug demo \
  --portfolio-name "Q3 Outlook" \
  --template /path/to/Climate_Metrics_Import_tempate.xlsx
```

Generated files are written under `runs/<run_id>/`. Review them before
committing because manifests and generated uploads can contain client or asset
context.

## Dashboard

Build dashboard data from the checked-in returned SCR examples:

```bash
python scripts/build_dashboard_data.py \
  --physical docs/output_examples/asset_1232_physical_risks.xlsx \
  --transition docs/output_examples/asset_1232_transition_risks.xlsx \
  --out dashboard/data/example_asset_1232.json
```

Run the static dashboard locally:

```bash
python -m http.server 8765
```

Open:

```text
http://localhost:8765/dashboard/
```

More detail is in [`dashboard/README.md`](dashboard/README.md).

## Docs

- [`docs/README.md`](docs/README.md): implementation notes
- [`docs/guide.md`](docs/guide.md): operator guide
- [`dashboard/README.md`](dashboard/README.md): local dashboard workflow
- [`docs/output_examples/schema.md`](docs/output_examples/schema.md):
  returned SCR output schema and usage notes
- [`docs/metadata/README.md`](docs/metadata/README.md): ClimateMetrics
  metadata source map and implementation notes

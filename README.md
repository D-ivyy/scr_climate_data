# SCR Climate Data

Utilities and documentation for exporting InfraSure asset rows into SCR's
climate-data upload format, then joining SCR's returned physical and
transition risk outputs back to InfraSure assets.

## Repository Scope

This repo contains:

- `scripts/export_scr_upload.py`: dev/prod DB to SCR upload exporter
- `docs/`: upload, manifest, output-schema, and ingestion notes
- `runs/.gitkeep`: placeholder for generated local outputs

This public repo intentionally does not commit vendor-provided workbooks,
returned SCR output workbooks, generated uploads, manifests, or database
credentials.

Local-only files expected by the current workflow:

```text
.env
docs/Climate_Metrics_Import_tempate.xlsx
docs/output_examples/*.xlsx
runs/<run_id>/*
```

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

Generated files are written under `runs/<run_id>/` and are ignored by git.

## Docs

- [`docs/README.md`](docs/README.md): implementation notes
- [`docs/guide.md`](docs/guide.md): operator guide
- [`docs/output_examples/schema.md`](docs/output_examples/schema.md):
  returned SCR output schema and usage notes

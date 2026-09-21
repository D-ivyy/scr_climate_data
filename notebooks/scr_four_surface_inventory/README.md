# SCR four-surface inventory

This investigation freezes and compares the current GCS source surfaces for:

- Solar PV physical risk;
- Solar PV transition risk;
- Onshore Wind physical risk; and
- Onshore Wind transition risk.

Run from the repository root:

```bash
/Users/divy/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 \
  notebooks/scr_four_surface_inventory/01_inventory_and_schema_profile.py
```

The script is read-only with respect to GCS. It lists objects, reads the
canonical grid, downloads a deterministic small workbook sample into a temporary
directory, and writes reproducible evidence under `outputs/`.

Expected outputs:

- `outputs/inventory_summary.json`
- `outputs/solar_missing_cells.csv`
- `outputs/schema_sample_summary.csv`
- `outputs/schema_profile.json`

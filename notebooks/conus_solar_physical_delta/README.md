# SCR Solar CONUS investigation notebooks

These notebooks investigate the SCR Solar photovoltaic workbook corpus in
`gs://infrasure-scr-data/physical_risks_exports/` before a production parser or
Parquet is built.

```text
canonical InfraSure grid (13,085 cells)
                  |
                  v
00 bucket/grid inventory
  filenames, IDs, labels, missing coverage
                  |
                  v
01 sampled workbook validation
  coordinates, schema, hazards, scenarios, factor availability
                  |
                  v
discussion + approved production plan
```

## Run order

1. Run `00_bucket_grid_inventory.ipynb`.
2. Run `01_sample_workbook_schema.ipynb`.
3. Extract the full corpus with `support/extract_overall_damage.mjs`, using
   process shards for reasonable runtime.
4. Run `02_full_overall_delta_distribution.ipynb` with `SCR_FULL_SHARD_DIR`
   pointing to those extraction shards.
5. Run `03_factor_stabilization_experiment.py` against the full extraction
   shard directory and canonical grid to compare raw, log-compressed,
   denominator-floor, and spatial candidates.
6. Review the dated lightweight outputs under `outputs/`.

Environment overrides:

| Variable | Purpose |
|---|---|
| `HAZARD_MODELING_ROOT` | Hazard_modeling repository containing the canonical grid |
| `SCR_CANONICAL_GRID` | Direct path to the served 13,085-cell CSV |
| `SCR_BUCKET_GLOB` | GCS workbook glob |
| `SCR_SAMPLE_DIR` | Local temporary workbook sample directory |
| `SCR_NODE_BIN` | Node.js executable used for artifact-tool |
| `SCR_NODE_MODULES` | `node_modules` directory containing `@oai/artifact-tool` |
| `SCR_FULL_SHARD_DIR` | Directory containing full-corpus extraction shard JSON files |

The notebooks write only review evidence. They do not publish or overwrite a
production Parquet. Raw SCR workbooks stay in GCS.

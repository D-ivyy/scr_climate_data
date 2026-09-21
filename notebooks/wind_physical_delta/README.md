# SCR Onshore Wind physical-delta investigation

This folder validates and then profiles the Onshore Wind physical-damage
surface before any applied factor is published.

Execution order:

1. `00_parser_parity.py` — compare the Cloud Run OOXML extractor with an
   independent `openpyxl` reference on deterministic current-source samples.
2. `01_full_extraction_and_factor_profile.py` — validate all Cloud Run shards
   and quantify baselines, metric gaps, extremes, inversions, and distributions.
4. Stabilization experiment — test the Solar method against Wind; do not copy
   the Solar parameters by assumption.
5. Governed Parquet build after the factor decision is documented.

The first validation writes:

`outputs/parser_parity.json`

The full-corpus profile writes:

- `outputs/<date>/full_extraction_profile.json`
- `outputs/<date>/factor_distribution_by_horizon.csv`
- `outputs/<date>/metric_unavailable_cells.csv`
- `outputs/<date>/factor_extremes.csv`

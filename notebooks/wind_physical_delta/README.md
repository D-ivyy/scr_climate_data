# SCR Onshore Wind physical-delta investigation

This folder validates and then profiles the Onshore Wind physical-damage
surface before any applied factor is published.

Execution order:

1. `00_parser_parity.py` — compare the Cloud Run OOXML extractor with an
   independent `openpyxl` reference on deterministic current-source samples.
2. `01_full_extraction_and_factor_profile.py` — validate all Cloud Run shards
   and quantify baselines, metric gaps, extremes, inversions, and distributions.
3. `02_nearest_fill_validation.py` — prove raw-field parity, donor completeness,
   late-emerging-value preservation, Solar-pattern overlap, and V2 behavior.
4. `03_prepare_research_package.py` — finalize immutable filled V1/V2 research
   metadata only after the nearest-fill validation passes.
5. Stabilization experiment — test the Solar method against Wind; do not copy
   the Solar parameters by assumption.
6. Recipient delivery build after the factor decision is documented.

The first validation writes:

`outputs/parser_parity.json`

The full-corpus profile writes:

- `outputs/<date>/full_extraction_profile.json`
- `outputs/<date>/factor_distribution_by_horizon.csv`
- `outputs/<date>/metric_unavailable_cells.csv`
- `outputs/<date>/factor_extremes.csv`

Nearest-fill validation writes:

- `outputs/<date>/nearest_fill_validation.json`
- `outputs/<date>/nearest_fill_longest_donors.csv`
- `outputs/<date>/nearest_fill_late_emerging_rows.csv`
- `outputs/<date>/nearest_fill_imputed_compression_rows.csv`

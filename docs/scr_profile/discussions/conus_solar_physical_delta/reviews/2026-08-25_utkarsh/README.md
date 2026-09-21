# Utkarsh review reports — 2026-08-25

These two reports were supplied by Utkarsh for review after the Solar CONUS
factor surface and V2 stabilization candidate had been built.

They are preserved as **content-complete attributed review evidence**. Two
trailing spaces were removed for repository Markdown hygiene; the wording,
figures, formulas, and structure are otherwise unchanged. Their findings and
recommendations are not automatically part of the canonical SCR method.
The InfraSure validation and current decision are recorded in
[`../../05_utkarsh_report_validation.md`](../../05_utkarsh_report_validation.md).
The cited V2 checks can be rerun with
[`validation_queries.sql`](validation_queries.sql).

## Source inventory

| Source file | Repository copy | Original source SHA-256 | Classification |
|---|---|---|---|
| `/Users/divy/Downloads/scr_climate_analysis_report.md` | [`scr_climate_analysis_report.md`](scr_climate_analysis_report.md) | `ab5ab5033fb36330929f384d202d868bc6e6bf757d1f356383dcadf525e16512` | Review evidence: source-pattern and scenario-inversion analysis |
| `/Users/divy/Downloads/scr_multiplier_edge_cases_and_stabilization_report.md` | [`scr_multiplier_edge_cases_and_stabilization_report.md`](scr_multiplier_edge_cases_and_stabilization_report.md) | `fefe8e4d97b1eb8fea44586b04426b7b0fe7e7f312cbc3177f47b3f985a773db` | Review evidence: proposed zero-baseline and multiplier framework |

## Governance boundary

- Preserve the original files in Downloads and the content-complete repository
  copies so Utkarsh's proposal remains auditable.
- Use the validation note—not these source reports—as the current implementation
  decision.
- Do not change the V2 Parquet, factor formula, dashboard calculation, or product
  horizon from these reports without a separate tested and approved decision.

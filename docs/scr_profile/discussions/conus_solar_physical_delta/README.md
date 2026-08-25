# SCR Solar CONUS physical-delta discussion

## Goal

Turn the SCR Solar photovoltaic export into one governed, canonical-grid-aligned
Parquet that preserves SCR's physical-damage values and derives transparent
2025-to-future change factors by scenario, year, and hazard.

```text
InfraSure canonical grid                         SCR Solar export
13,085 cells                                    11,928 XLSX files
cell_id + center                               same cell_id in filename
          \                                         /
           +--------------- reconcile -------------+
                                |
                                v
                   raw SCR physical-damage values
                                |
                       baseline = 2025
                                |
                                v
              factor = |future damage| / |2025 damage|
                                |
                                v
          one canonical-grid Parquet with provenance/status
```

This is an expected-loss scaling input, not a rerun of InfraSure hazard models.
The V1 candidate is the overall asset rollup, `adjustedTotalDamage`. Hazard
damage, disruption, and combined value remain source-reconciliation and research
evidence; they are not required fields in the first final Parquet.

## Current evidence

- [Investigation findings](01_investigation_findings.md)
- [Decisions before production](02_decisions_before_production.md)
- [Full overall-delta distribution](03_full_overall_delta_distribution.md)
- [Factor stabilization experiment](04_factor_stabilization_experiment.md)
- [Validation of Utkarsh's two follow-up reports](05_utkarsh_report_validation.md)
- [Execution plan](../../plans/SCR%20Solar%20CONUS%20Physical%20Delta%20Parquet%20Plan.md)
- [Reproducible notebooks](../../../../notebooks/conus_solar_physical_delta/README.md)

## Attributed review evidence

Content-complete copies of Utkarsh's original 2026-08-25 reports are preserved under
[`reviews/2026-08-25_utkarsh/`](reviews/2026-08-25_utkarsh/). They are review
inputs, not automatic changes to the governed method.

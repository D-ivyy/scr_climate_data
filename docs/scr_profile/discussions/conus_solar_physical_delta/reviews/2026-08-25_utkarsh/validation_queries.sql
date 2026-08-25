-- Reproduce the V2 checks cited in 05_utkarsh_report_validation.md.
-- Run from the scr_climate_data repository root with DuckDB.

CREATE OR REPLACE VIEW scr_v2 AS
SELECT *
FROM read_parquet(
  'runs/2026-08-18__solar_conus_overall_delta_v2/scr_solar_conus_overall_delta_v2.parquet'
);

-- Surface and compression inventory.
SELECT
  count(*) AS row_count,
  count(DISTINCT cell_id) AS cell_count,
  min(factor_filled) AS raw_min,
  max(factor_filled) AS raw_max,
  min(factor_filled_stabilized_candidate) AS candidate_min,
  max(factor_filled_stabilized_candidate) AS candidate_max,
  count(*) FILTER (WHERE filled_factor_was_compressed) AS compressed_rows,
  count(DISTINCT cell_id) FILTER (WHERE filled_factor_was_compressed) AS compressed_cells
FROM scr_v2;

-- Risk-reduction counts used in Utkarsh's first report.
SELECT
  scenario,
  horizon,
  count(*) FILTER (WHERE factor_filled <= 0.995) AS reduction_cells
FROM scr_v2
WHERE horizon IN (2050, 2100)
GROUP BY scenario, horizon
ORDER BY scenario, horizon;

-- Scenario crossover counts and spreads using the report's >0.5% rule.
WITH paired AS (
  SELECT
    cell_id,
    horizon,
    max(factor_filled_stabilized_candidate)
      FILTER (WHERE scenario = 'ssp2-4.5') AS factor_ssp2,
    max(factor_filled_stabilized_candidate)
      FILTER (WHERE scenario = 'ssp5-8.5') AS factor_ssp5
  FROM scr_v2
  GROUP BY cell_id, horizon
), spreads AS (
  SELECT *, 100 * (factor_ssp2 - factor_ssp5) AS spread_pct
  FROM paired
)
SELECT
  horizon,
  count(*) FILTER (WHERE spread_pct > 0.5) AS crossover_cells,
  avg(spread_pct) FILTER (WHERE spread_pct > 0.5) AS mean_spread_pct,
  median(spread_pct) FILTER (WHERE spread_pct > 0.5) AS median_spread_pct,
  max(spread_pct) FILTER (WHERE spread_pct > 0.5) AS max_spread_pct
FROM spreads
WHERE horizon IN (2040, 2050, 2070, 2080, 2100)
GROUP BY horizon
ORDER BY horizon;

-- Determine whether compressed rows are universally explained by one tiny
-- denominator threshold.
SELECT
  count(*) FILTER (
    WHERE filled_factor_was_compressed
      AND baseline_damage_magnitude_filled < 1e-4
  ) AS compressed_rows_below_1e4,
  count(*) FILTER (
    WHERE filled_factor_was_compressed
      AND baseline_damage_magnitude_filled >= 1e-4
  ) AS compressed_rows_at_or_above_1e4
FROM scr_v2;

-- Concrete New Jersey edge case.
SELECT
  cell_id,
  state_abbr,
  scenario,
  horizon,
  baseline_damage_magnitude_filled,
  future_damage_magnitude_filled,
  absolute_change_magnitude_filled,
  factor_filled,
  factor_filled_stabilized_candidate
FROM scr_v2
WHERE cell_id = 287704 AND horizon = 2050
ORDER BY scenario;

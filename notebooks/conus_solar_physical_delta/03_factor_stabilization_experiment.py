#!/usr/bin/env python3
"""Compare candidate stabilizations for SCR overall-damage factors.

This is an investigation script. It never edits the canonical Parquet. Inputs
are the JSON result shards emitted by the Cloud Run total-damage extractor and
the canonical CONUS grid CSV.
"""

from __future__ import annotations

import argparse
import csv
import glob
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path


SCENARIOS = ("ssp2-4.5", "ssp5-8.5")
HORIZONS = tuple(range(2025, 2101, 5))
FINANCIAL_BASE_RATES = (0.001, 0.005, 0.01, 0.02, 0.05, 0.10)
FINANCIAL_LIMITS = (0.10, 0.50, 1.00)

METHODS = {
    "raw": {"kind": "raw"},
    "hard_cap_5": {"kind": "hard_cap", "floor": 0.2, "ceiling": 5.0},
    "power_0_5": {"kind": "power", "alpha": 0.5},
    "symmetric_log": {"kind": "symmetric_log"},
    "baseline_floor_1e-4": {"kind": "baseline_floor", "floor": 1e-4},
    "soft_log_t1_5_c5": {"kind": "soft_log", "start": 1.5, "ceiling": 5.0},
    "soft_log_t2_c3": {"kind": "soft_log", "start": 2.0, "ceiling": 3.0},
    "soft_log_t2_c5": {"kind": "soft_log", "start": 2.0, "ceiling": 5.0},
    "soft_log_t2_c10": {"kind": "soft_log", "start": 2.0, "ceiling": 10.0},
    "soft_log_t3_c5": {"kind": "soft_log", "start": 3.0, "ceiling": 5.0},
    "soft_log_t3_c10": {"kind": "soft_log", "start": 3.0, "ceiling": 10.0},
    "soft_log_t5_c10": {"kind": "soft_log", "start": 5.0, "ceiling": 10.0},
    "soft_log_arctan_t3_c5": {"kind": "soft_log_arctan", "start": 3.0, "ceiling": 5.0},
    "spatial_ratio_3x3": {"kind": "spatial_ratio"},
    "spatial_outlier_replace": {
        "kind": "spatial_outlier",
        "upper_trigger": 5.0,
        "lower_trigger": 0.2,
        "neighbor_ratio": 5.0,
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--shards", type=Path, required=True)
    parser.add_argument("--grid", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def percentile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] * (upper - position) + ordered[upper] * (position - lower)


def load_totals(shard_root: Path) -> dict[int, dict]:
    observed: dict[int, dict] = {}
    paths = sorted(glob.glob(str(shard_root / "**" / "results.json"), recursive=True))
    if not paths:
        raise ValueError(f"No results.json files found under {shard_root}")
    for path in paths:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        for item in payload["files"]:
            if item["status"] != "ok":
                raise ValueError(f"Source extraction error in {path}: {item}")
            cell_id = int(item["cellId"])
            if cell_id in observed:
                raise ValueError(f"Duplicate cell {cell_id}")
            observed[cell_id] = item["totals"]
    return observed


def load_grid(path: Path) -> tuple[dict[int, tuple[int, int]], dict[tuple[int, int], int]]:
    by_cell: dict[int, tuple[int, int]] = {}
    by_index: dict[tuple[int, int], int] = {}
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            cell_id = int(row["cell_id"])
            index = (int(row["lat_idx"]), int(row["lon_idx"]))
            by_cell[cell_id] = index
            by_index[index] = cell_id
    return by_cell, by_index


def soft_log_upper(value: float, start: float, ceiling: float) -> float:
    if value <= start:
        return value
    log_start = math.log(start)
    log_ceiling = math.log(ceiling)
    width = log_ceiling - log_start
    return math.exp(log_start + width * math.tanh((math.log(value) - log_start) / width))


def soft_log_symmetric(value: float, start: float, ceiling: float) -> float:
    if value >= 1:
        return soft_log_upper(value, start, ceiling)
    return 1 / soft_log_upper(1 / value, start, ceiling)


def soft_log_arctan_upper(value: float, start: float, ceiling: float) -> float:
    if value <= start:
        return value
    log_start = math.log(start)
    log_ceiling = math.log(ceiling)
    width = log_ceiling - log_start
    scaled_excess = (math.log(value) - log_start) / width
    bounded_excess = (2 / math.pi) * math.atan((math.pi / 2) * scaled_excess)
    return math.exp(log_start + width * bounded_excess)


def soft_log_arctan_symmetric(value: float, start: float, ceiling: float) -> float:
    if 1 / start <= value <= start:
        return value
    if value > start:
        return soft_log_arctan_upper(value, start, ceiling)
    return 1 / soft_log_arctan_upper(1 / value, start, ceiling)


def transform_scalar(config: dict, raw: float, baseline: float, future: float) -> float:
    kind = config["kind"]
    if kind == "raw":
        return raw
    if kind == "hard_cap":
        return min(config["ceiling"], max(config["floor"], raw))
    if kind == "power":
        return math.exp(config["alpha"] * math.log(raw))
    if kind == "symmetric_log":
        return 1 + math.log(raw) if raw >= 1 else 1 / (1 + math.log(1 / raw))
    if kind == "baseline_floor":
        return 1 + (future - baseline) / max(baseline, config["floor"])
    if kind == "soft_log":
        return soft_log_symmetric(raw, config["start"], config["ceiling"])
    if kind == "soft_log_arctan":
        return soft_log_arctan_symmetric(raw, config["start"], config["ceiling"])
    raise ValueError(f"{kind} is not a scalar transformation")


def immediate_neighbors(
    cell_id: int,
    available: set[int],
    by_cell: dict[int, tuple[int, int]],
    by_index: dict[tuple[int, int], int],
    include_self: bool,
) -> list[int]:
    lat_index, lon_index = by_cell[cell_id]
    cells = []
    for lat_delta in (-1, 0, 1):
        for lon_delta in (-1, 0, 1):
            if not include_self and lat_delta == 0 and lon_delta == 0:
                continue
            candidate = by_index.get((lat_index + lat_delta, lon_index + lon_delta))
            if candidate in available:
                cells.append(candidate)
    return cells


def spatial_values(
    config: dict,
    raw: dict[int, float],
    baseline: dict[int, float],
    future: dict[int, float],
    by_cell: dict[int, tuple[int, int]],
    by_index: dict[tuple[int, int], int],
) -> tuple[dict[int, float], int]:
    result = {}
    replaced = 0
    available = set(raw)
    for cell_id, factor in raw.items():
        region = immediate_neighbors(cell_id, available, by_cell, by_index, include_self=True)
        regional_ratio = statistics.median(future[item] for item in region) / statistics.median(
            baseline[item] for item in region
        )
        if config["kind"] == "spatial_ratio":
            result[cell_id] = regional_ratio
            replaced += not math.isclose(factor, regional_ratio, rel_tol=1e-12, abs_tol=1e-15)
            continue
        neighbors = immediate_neighbors(cell_id, available, by_cell, by_index, include_self=False)
        neighbor_median = statistics.median(raw[item] for item in neighbors) if neighbors else factor
        high_outlier = (
            factor > config["upper_trigger"]
            and neighbor_median > 0
            and factor / neighbor_median > config["neighbor_ratio"]
        )
        low_outlier = (
            factor < config["lower_trigger"]
            and factor > 0
            and neighbor_median / factor > config["neighbor_ratio"]
        )
        if high_outlier or low_outlier:
            result[cell_id] = regional_ratio
            replaced += 1
        else:
            result[cell_id] = factor
    return result, replaced


def roughness(
    values: dict[int, float],
    by_cell: dict[int, tuple[int, int]],
    by_index: dict[tuple[int, int], int],
) -> tuple[float, float]:
    deviations = []
    available = set(values)
    for cell_id, value in values.items():
        neighbors = immediate_neighbors(cell_id, available, by_cell, by_index, include_self=False)
        if neighbors:
            local = statistics.median(math.log(values[item]) for item in neighbors)
            deviations.append(abs(math.log(value) - local))
    return statistics.median(deviations), percentile(deviations, 0.99)


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=list(rows[0]),
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    observed = load_totals(args.shards)
    by_cell, by_index = load_grid(args.grid)
    unknown = sorted(set(observed) - set(by_cell))
    if unknown:
        raise ValueError(f"Observed data contains {len(unknown)} noncanonical cells")

    baseline_maps: dict[tuple[str, int], dict[int, float]] = {}
    future_maps: dict[tuple[str, int], dict[int, float]] = {}
    raw_maps: dict[tuple[str, int], dict[int, float]] = {}
    for scenario in SCENARIOS:
        for horizon in HORIZONS:
            baseline = {
                cell_id: abs(float(totals[scenario]["2025"])) for cell_id, totals in observed.items()
            }
            future = {
                cell_id: abs(float(totals[scenario][str(horizon)]))
                for cell_id, totals in observed.items()
            }
            baseline_maps[(scenario, horizon)] = baseline
            future_maps[(scenario, horizon)] = future
            raw_maps[(scenario, horizon)] = {
                cell_id: future[cell_id] / baseline[cell_id] for cell_id in observed
            }

    horizon_rows = []
    method_rows = []
    financial_rows = []
    mapping_rows = []
    experiment = {
        "observed_cells": len(observed),
        "scenarios": list(SCENARIOS),
        "horizons": list(HORIZONS),
        "methods": METHODS,
        "results": {},
    }
    mapping_inputs = (0.0394736842, 0.1, 0.2, 0.5, 1, 1.2, 1.5, 2, 3, 5, 10, 25, 100, 1556.745114921)

    for method_name, config in METHODS.items():
        adjusted_maps: dict[tuple[str, int], dict[int, float]] = {}
        changed_total = 0
        core_errors = []
        method_replaced = 0
        for key, raw_values in raw_maps.items():
            baseline = baseline_maps[key]
            future = future_maps[key]
            if config["kind"].startswith("spatial_"):
                adjusted, replaced = spatial_values(
                    config, raw_values, baseline, future, by_cell, by_index
                )
                method_replaced += replaced
            else:
                adjusted = {
                    cell_id: transform_scalar(
                        config, factor, baseline[cell_id], future[cell_id]
                    )
                    for cell_id, factor in raw_values.items()
                }
            adjusted_maps[key] = adjusted
            changed_total += sum(
                not math.isclose(adjusted[cell_id], factor, rel_tol=1e-12, abs_tol=1e-15)
                for cell_id, factor in raw_values.items()
            )
            core_errors.extend(
                abs(math.log(adjusted[cell_id] / factor))
                for cell_id, factor in raw_values.items()
                if 0.5 <= factor <= 2.0
            )
            values = list(adjusted.values())
            scenario, horizon = key
            horizon_rows.append(
                {
                    "method": method_name,
                    "scenario": scenario,
                    "horizon": horizon,
                    "minimum": min(values),
                    "median": percentile(values, 0.5),
                    "p90": percentile(values, 0.9),
                    "p95": percentile(values, 0.95),
                    "p99": percentile(values, 0.99),
                    "p99_5": percentile(values, 0.995),
                    "p99_9": percentile(values, 0.999),
                    "maximum": max(values),
                    "above_2": sum(value > 2 for value in values),
                    "above_5": sum(value > 5 for value in values),
                    "above_10": sum(value > 10 for value in values),
                    "below_0_5": sum(value < 0.5 for value in values),
                }
            )

        temporal_reversals = 0
        temporal_ties_created = 0
        for scenario in SCENARIOS:
            for previous_horizon, horizon in zip(HORIZONS, HORIZONS[1:]):
                raw_previous = raw_maps[(scenario, previous_horizon)]
                raw_current = raw_maps[(scenario, horizon)]
                adj_previous = adjusted_maps[(scenario, previous_horizon)]
                adj_current = adjusted_maps[(scenario, horizon)]
                for cell_id in observed:
                    raw_difference = raw_current[cell_id] - raw_previous[cell_id]
                    adjusted_difference = adj_current[cell_id] - adj_previous[cell_id]
                    raw_zero = math.isclose(raw_difference, 0, rel_tol=1e-12, abs_tol=1e-15)
                    adjusted_zero = math.isclose(
                        adjusted_difference, 0, rel_tol=1e-12, abs_tol=1e-15
                    )
                    if not raw_zero and not adjusted_zero and raw_difference * adjusted_difference < 0:
                        temporal_reversals += 1
                    if not raw_zero and adjusted_zero:
                        temporal_ties_created += 1

        scenario_reversals = 0
        scenario_ties_created = 0
        for horizon in HORIZONS:
            raw_low = raw_maps[(SCENARIOS[0], horizon)]
            raw_high = raw_maps[(SCENARIOS[1], horizon)]
            adj_low = adjusted_maps[(SCENARIOS[0], horizon)]
            adj_high = adjusted_maps[(SCENARIOS[1], horizon)]
            for cell_id in observed:
                raw_difference = raw_high[cell_id] - raw_low[cell_id]
                adjusted_difference = adj_high[cell_id] - adj_low[cell_id]
                raw_zero = math.isclose(raw_difference, 0, rel_tol=1e-12, abs_tol=1e-15)
                adjusted_zero = math.isclose(
                    adjusted_difference, 0, rel_tol=1e-12, abs_tol=1e-15
                )
                if not raw_zero and not adjusted_zero and raw_difference * adjusted_difference < 0:
                    scenario_reversals += 1
                if not raw_zero and adjusted_zero:
                    scenario_ties_created += 1

        roughness_results = {}
        for scenario in SCENARIOS:
            median_roughness, p99_roughness = roughness(
                adjusted_maps[(scenario, 2100)], by_cell, by_index
            )
            roughness_results[scenario] = {
                "median_absolute_log_deviation": median_roughness,
                "p99_absolute_log_deviation": p99_roughness,
            }

        for scenario in SCENARIOS:
            values_2100 = list(adjusted_maps[(scenario, 2100)].values())
            for base_rate in FINANCIAL_BASE_RATES:
                for limit in FINANCIAL_LIMITS:
                    financial_rows.append(
                        {
                            "method": method_name,
                            "scenario": scenario,
                            "horizon": 2100,
                            "baseline_eal_rate": base_rate,
                            "future_eal_rate_limit": limit,
                            "cells_exceeding_limit": sum(
                                base_rate * value > limit for value in values_2100
                            ),
                            "share_exceeding_limit": sum(
                                base_rate * value > limit for value in values_2100
                            )
                            / len(values_2100),
                        }
                    )

        for factor in mapping_inputs:
            if config["kind"].startswith("spatial_") or config["kind"] == "baseline_floor":
                continue
            mapping_rows.append(
                {
                    "method": method_name,
                    "factor_raw": factor,
                    "factor_adjusted": transform_scalar(config, factor, 1.0, factor),
                }
            )

        all_adjusted = [
            value for mapping in adjusted_maps.values() for value in mapping.values()
        ]
        result = {
            "changed_rows": changed_total,
            "changed_share": changed_total / len(all_adjusted),
            "explicit_spatial_replacements": method_replaced,
            "core_mean_absolute_log_error": statistics.fmean(core_errors),
            "core_max_absolute_log_error": max(core_errors),
            "global_minimum": min(all_adjusted),
            "global_maximum": max(all_adjusted),
            "temporal_reversals": temporal_reversals,
            "temporal_ties_created": temporal_ties_created,
            "scenario_reversals": scenario_reversals,
            "scenario_ties_created": scenario_ties_created,
            "spatial_roughness_2100": roughness_results,
        }
        experiment["results"][method_name] = result
        method_rows.append({"method": method_name, **result, "spatial_roughness_2100": json.dumps(roughness_results, sort_keys=True)})

    write_csv(args.output_dir / "factor_stabilization_method_summary.csv", method_rows)
    write_csv(args.output_dir / "factor_stabilization_horizon_summary.csv", horizon_rows)
    write_csv(args.output_dir / "factor_stabilization_financial_stress.csv", financial_rows)
    write_csv(args.output_dir / "factor_stabilization_mapping_examples.csv", mapping_rows)
    (args.output_dir / "factor_stabilization_experiment.json").write_text(
        json.dumps(experiment, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"status": "ok", "output_dir": str(args.output_dir), "methods": len(METHODS)}))


if __name__ == "__main__":
    main()

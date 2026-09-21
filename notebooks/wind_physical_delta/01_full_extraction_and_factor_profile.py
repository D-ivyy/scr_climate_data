#!/usr/bin/env python3
"""Validate full Wind extraction and profile raw overall-damage factors."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any


SCENARIOS = ("ssp2-4.5", "ssp5-8.5")
HORIZONS = tuple(range(2025, 2101, 5))
BASELINE_YEAR = 2025


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--shards", required=True, type=Path)
    parser.add_argument("--grid", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--inventory-sha256", required=True)
    return parser.parse_args()


def percentile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = (len(ordered) - 1) * q
    lower, upper = math.floor(index), math.ceil(index)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] * (upper - index) + ordered[upper] * (index - lower)


def describe(values: list[float]) -> dict[str, float | int | None]:
    return {
        "count": len(values),
        "min": min(values) if values else None,
        "p01": percentile(values, 0.01),
        "p05": percentile(values, 0.05),
        "p25": percentile(values, 0.25),
        "median": percentile(values, 0.5),
        "p75": percentile(values, 0.75),
        "p95": percentile(values, 0.95),
        "p99": percentile(values, 0.99),
        "max": max(values) if values else None,
    }


def load_grid(path: Path) -> dict[int, dict[str, Any]]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    return {
        int(row["cell_id"]): {
            "cell_id": int(row["cell_id"]),
            "lat_idx": int(row["lat_idx"]),
            "lon_idx": int(row["lon_idx"]),
            "lat_center": float(row["lat_center"]),
            "lon_center": float(row["lon_center"]),
            "state_abbr": row["state_abbr"],
        }
        for row in rows
    }


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    grid = load_grid(args.grid)
    shard_paths = sorted(args.shards.glob("task=*/results.json"))
    if not shard_paths:
        raise ValueError(f"No result shards under {args.shards}")

    task_indexes = []
    task_counts = set()
    inventory_hashes = set()
    files = []
    for path in shard_paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        task_indexes.append(int(payload["task_index"]))
        task_counts.add(int(payload["task_count"]))
        inventory_hashes.add(payload["source_inventory_sha256"])
        files.extend(payload["files"])

    errors = [item for item in files if item["status"] != "ok"]
    successful = [item for item in files if item["status"] == "ok"]
    cell_ids = [int(item["cellId"]) for item in successful]
    header_hashes = {
        hashlib.sha256(
            json.dumps(item["headers"], separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        for item in successful
    }
    files_by_cell = {int(item["cellId"]): item for item in successful}

    extraction_checks = {
        "shard_count_is_128": len(shard_paths) == 128,
        "task_indexes_are_0_through_127": sorted(task_indexes) == list(range(128)),
        "task_count_is_128": task_counts == {128},
        "inventory_sha_matches": inventory_hashes == {args.inventory_sha256},
        "all_files_parsed": not errors,
        "file_count_is_13085": len(successful) == 13085,
        "unique_cell_count_is_13085": len(set(cell_ids)) == 13085,
        "canonical_cell_set_matches": set(cell_ids) == set(grid),
        "all_row_counts_are_986": {item["rowCount"] for item in successful} == {986},
        "one_header_schema": len(header_hashes) == 1,
    }
    if not all(extraction_checks.values()):
        raise ValueError(f"Extraction QA failed: {extraction_checks}")

    factor_rows = []
    baseline_profile = {}
    unavailable_by_scenario: dict[str, set[int]] = {}
    for scenario in SCENARIOS:
        baseline_values = []
        unavailable = set()
        for cell_id, item in files_by_cell.items():
            baseline = item["totals"].get(scenario, {}).get(str(BASELINE_YEAR))
            if baseline is None:
                unavailable.add(cell_id)
            else:
                baseline_values.append(abs(float(baseline)))
        unavailable_by_scenario[scenario] = unavailable
        baseline_profile[scenario] = {
            **describe(baseline_values),
            "unavailable_cell_count": len(unavailable),
            "zero_baseline_count": sum(value == 0 for value in baseline_values),
            "below_1e_8_count": sum(value < 1e-8 for value in baseline_values),
            "below_1e_6_count": sum(value < 1e-6 for value in baseline_values),
        }

        for cell_id, item in files_by_cell.items():
            totals = item["totals"].get(scenario, {})
            baseline_raw = totals.get(str(BASELINE_YEAR))
            baseline_magnitude = None if baseline_raw is None else abs(float(baseline_raw))
            for horizon in HORIZONS:
                future_raw = totals.get(str(horizon))
                future_magnitude = None if future_raw is None else abs(float(future_raw))
                factor = None
                if (
                    baseline_magnitude is not None
                    and baseline_magnitude > 0
                    and future_magnitude is not None
                ):
                    factor = future_magnitude / baseline_magnitude
                if baseline_magnitude is None and future_magnitude is None:
                    status = "baseline_and_future_unavailable"
                elif baseline_magnitude is None:
                    status = "baseline_unavailable_future_available"
                elif baseline_magnitude == 0:
                    status = "zero_baseline"
                elif future_magnitude is None:
                    status = "future_unavailable"
                else:
                    status = "observed_factor"
                factor_rows.append(
                    {
                        "cell_id": cell_id,
                        "state_abbr": grid[cell_id]["state_abbr"],
                        "lat_center": grid[cell_id]["lat_center"],
                        "lon_center": grid[cell_id]["lon_center"],
                        "scenario": scenario,
                        "horizon": horizon,
                        "baseline_damage_raw": baseline_raw,
                        "future_damage_raw": future_raw,
                        "baseline_damage_magnitude": baseline_magnitude,
                        "future_damage_magnitude": future_magnitude,
                        "factor_raw": factor,
                        "percent_change_raw": None if factor is None else factor - 1,
                        "factor_status": status,
                        "source_uri": (
                            "gs://infrasure-scr-data/onshore_wind/physical_risk/"
                            + item["filename"]
                        ),
                    }
                )

    horizon_rows = []
    for scenario in SCENARIOS:
        for horizon in HORIZONS:
            selected = [
                row
                for row in factor_rows
                if row["scenario"] == scenario and row["horizon"] == horizon
            ]
            values = [row["factor_raw"] for row in selected if row["factor_raw"] is not None]
            horizon_rows.append(
                {
                    "scenario": scenario,
                    "horizon": horizon,
                    **describe(values),
                    "missing_factor_count": len(selected) - len(values),
                    "factor_below_one_third_count": sum(value < 1 / 3 for value in values),
                    "factor_above_three_count": sum(value > 3 for value in values),
                    "factor_above_five_count": sum(value > 5 for value in values),
                }
            )

    with (args.output_dir / "factor_distribution_by_horizon.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.DictWriter(
            handle, fieldnames=list(horizon_rows[0]), lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(horizon_rows)

    unavailable_union = set().union(*unavailable_by_scenario.values())
    unavailable_rows = []
    for cell_id in sorted(unavailable_union):
        item = files_by_cell[cell_id]
        row = dict(grid[cell_id])
        row["source_uri"] = (
            "gs://infrasure-scr-data/onshore_wind/physical_risk/" + item["filename"]
        )
        for scenario in SCENARIOS:
            totals = item["totals"].get(scenario, {})
            row[f"{scenario}_baseline_available"] = totals.get("2025") is not None
            row[f"{scenario}_future_nonnull_count"] = sum(
                totals.get(str(horizon)) is not None for horizon in HORIZONS[1:]
            )
        unavailable_rows.append(row)

    with (args.output_dir / "metric_unavailable_cells.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.DictWriter(
            handle, fieldnames=list(unavailable_rows[0]), lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(unavailable_rows)

    observed_rows = [row for row in factor_rows if row["factor_raw"] is not None]
    lowest = sorted(observed_rows, key=lambda row: row["factor_raw"])[:100]
    highest = sorted(observed_rows, key=lambda row: row["factor_raw"], reverse=True)[:100]
    extreme_rows = [dict(rank=index + 1, tail="lowest", **row) for index, row in enumerate(lowest)]
    extreme_rows += [dict(rank=index + 1, tail="highest", **row) for index, row in enumerate(highest)]
    with (args.output_dir / "factor_extremes.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.DictWriter(
            handle, fieldnames=list(extreme_rows[0]), lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(extreme_rows)

    state_counts = Counter(grid[cell_id]["state_abbr"] for cell_id in unavailable_union)
    all_factors = [row["factor_raw"] for row in observed_rows]
    summary = {
        "status": "passed",
        "extraction_checks": extraction_checks,
        "cloud_run": {
            "task_count": 128,
            "inventory_sha256": args.inventory_sha256,
            "workbook_count": len(successful),
            "parse_error_count": len(errors),
            "header_schema_sha256": next(iter(header_hashes)),
        },
        "metric": "adjustedTotalDamage",
        "baseline_year": BASELINE_YEAR,
        "scenarios": list(SCENARIOS),
        "horizons": list(HORIZONS),
        "baseline_profile": baseline_profile,
        "metric_unavailable": {
            "union_cell_count": len(unavailable_union),
            "sets_identical_across_scenarios": (
                unavailable_by_scenario[SCENARIOS[0]]
                == unavailable_by_scenario[SCENARIOS[1]]
            ),
            "by_state": dict(sorted(state_counts.items())),
        },
        "raw_factor_profile": {
            **describe(all_factors),
            "factor_below_one_third_count": sum(value < 1 / 3 for value in all_factors),
            "factor_above_three_count": sum(value > 3 for value in all_factors),
            "factor_above_five_count": sum(value > 5 for value in all_factors),
        },
        "iso_rto_included": False,
        "interpretation": (
            "Raw factor evidence only. Metric-unavailable cells and extreme ratios require "
            "a separate fill/stabilization decision before product use."
        ),
    }
    (args.output_dir / "full_extraction_profile.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "status": summary["status"],
                "workbooks": len(successful),
                "metric_unavailable_cells": len(unavailable_union),
                "raw_factor_min": summary["raw_factor_profile"]["min"],
                "raw_factor_max": summary["raw_factor_profile"]["max"],
            }
        )
    )


if __name__ == "__main__":
    main()

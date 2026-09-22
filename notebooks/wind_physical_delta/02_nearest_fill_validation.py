#!/usr/bin/env python3
"""Validate the Wind nearest-cell V1 and stabilized V2 candidates."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

import pyarrow.parquet as pq


KEY = ("cell_id", "scenario", "horizon")
RAW_COLUMNS = (
    "cell_id",
    "lat_idx",
    "lon_idx",
    "lat_center",
    "lon_center",
    "state_abbr",
    "asset_type",
    "ticcs_subclass",
    "scenario",
    "baseline_year",
    "horizon",
    "years_from_baseline",
    "scr_metric_name",
    "baseline_damage_raw",
    "future_damage_raw",
    "baseline_damage_magnitude_raw",
    "future_damage_magnitude_raw",
    "absolute_change_magnitude_raw",
    "factor_raw",
    "percent_change_raw",
    "source_uri",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-v1", required=True, type=Path)
    parser.add_argument("--filled-v1", required=True, type=Path)
    parser.add_argument("--filled-v1-manifest", required=True, type=Path)
    parser.add_argument("--filled-v2", required=True, type=Path)
    parser.add_argument("--filled-v2-qa", required=True, type=Path)
    parser.add_argument("--solar-old-missing", required=True, type=Path)
    parser.add_argument("--solar-current-missing", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def percentile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * q
    lower, upper = math.floor(position), math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] * (upper - position) + ordered[upper] * (position - lower)


def csv_ids(path: Path) -> set[int]:
    with path.open(newline="", encoding="utf-8") as handle:
        return {int(row["cell_id"]) for row in csv.DictReader(handle)}


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    raw = pq.read_table(args.raw_v1)
    filled = pq.read_table(args.filled_v1)
    v2 = pq.read_table(args.filled_v2)
    manifest = json.loads(args.filled_v1_manifest.read_text(encoding="utf-8"))
    v2_qa = json.loads(args.filled_v2_qa.read_text(encoding="utf-8"))

    checks: dict[str, bool] = {}
    checks["row_count_418720"] = raw.num_rows == filled.num_rows == v2.num_rows == 418_720
    checks["key_order_preserved"] = all(raw[name].equals(filled[name]) for name in KEY)
    checks["raw_source_fields_preserved"] = all(
        raw[name].equals(filled[name]) for name in RAW_COLUMNS
    )
    preserved_v1_columns = [
        name for name in filled.column_names if name != "schema_version"
    ]
    checks["v1_columns_preserved_in_v2"] = all(
        filled[name].equals(v2[name]) for name in preserved_v1_columns
    )
    checks["v2_source_schema_version_preserved"] = set(
        v2["source_schema_version"].to_pylist()
    ) == {"scr_wind_overall_delta_v1_filled"}

    cell_ids = filled["cell_id"].to_pylist()
    states = filled["state_abbr"].to_pylist()
    scenarios = filled["scenario"].to_pylist()
    horizons = filled["horizon"].to_pylist()
    raw_baselines = filled["baseline_damage_raw"].to_pylist()
    raw_futures = filled["future_damage_raw"].to_pylist()
    raw_factors = filled["factor_raw"].to_pylist()
    filled_factors = filled["factor_filled"].to_pylist()
    imputed = filled["is_imputed"].to_pylist()
    donors = filled["source_cell_id"].to_pylist()
    distances = filled["donor_distance_km"].to_pylist()
    statuses = filled["quality_status"].to_pylist()
    compressed = v2["filled_factor_was_compressed"].to_pylist()

    state_by_cell: dict[int, str] = {}
    rows_by_cell: Counter[int] = Counter()
    donor_by_cell: dict[int, int] = {}
    distance_by_cell: dict[int, float] = {}
    future_counts: dict[int, Counter[str]] = defaultdict(Counter)
    late_rows: list[dict] = []
    imputed_compressed_rows: list[dict] = []
    imputed_cells: set[int] = set()

    for index, cell_id in enumerate(cell_ids):
        state_by_cell[cell_id] = states[index]
        if imputed[index]:
            imputed_cells.add(cell_id)
            rows_by_cell[cell_id] += 1
            donor_by_cell[cell_id] = donors[index]
            distance_by_cell[cell_id] = distances[index]
            if raw_baselines[index] is None and raw_futures[index] is not None:
                future_counts[cell_id][scenarios[index]] += 1
                late_rows.append(
                    {
                        "cell_id": cell_id,
                        "state_abbr": states[index],
                        "scenario": scenarios[index],
                        "horizon": horizons[index],
                        "future_damage_raw": raw_futures[index],
                        "source_cell_id": donors[index],
                        "donor_distance_km": distances[index],
                    }
                )
            if compressed[index]:
                imputed_compressed_rows.append(
                    {
                        "cell_id": cell_id,
                        "state_abbr": states[index],
                        "scenario": scenarios[index],
                        "horizon": horizons[index],
                        "factor_filled": filled_factors[index],
                        "source_cell_id": donors[index],
                        "donor_distance_km": distances[index],
                    }
                )

    unique_distances = [distance_by_cell[cell_id] for cell_id in sorted(imputed_cells)]
    longest = []
    for cell_id in sorted(imputed_cells, key=lambda item: (-distance_by_cell[item], item))[:20]:
        donor = donor_by_cell[cell_id]
        longest.append(
            {
                "cell_id": cell_id,
                "state_abbr": state_by_cell[cell_id],
                "source_cell_id": donor,
                "source_state_abbr": state_by_cell[donor],
                "donor_distance_km": distance_by_cell[cell_id],
            }
        )

    solar_old = csv_ids(args.solar_old_missing)
    solar_current = csv_ids(args.solar_current_missing)
    overlap = imputed_cells & solar_old
    wind_only = imputed_cells - solar_old
    solar_only = solar_old - imputed_cells

    checks.update(
        {
            "unique_key": len(set(zip(cell_ids, scenarios, horizons))) == filled.num_rows,
            "raw_factor_null_count_35744": sum(value is None for value in raw_factors) == 35_744,
            "filled_factor_null_count_zero": all(value is not None for value in filled_factors),
            "imputed_cell_count_1117": len(imputed_cells) == 1_117,
            "each_imputed_cell_has_32_rows": set(rows_by_cell.values()) == {32},
            "imputed_status_is_explicit": {
                statuses[index] for index, flag in enumerate(imputed) if flag
            }
            == {"imputed_metric_unavailable_nearest"},
            "observed_rows_not_imputed": all(
                (flag or status == "observed")
                for flag, status in zip(imputed, statuses)
            ),
            "donors_are_non_imputed_cells": all(
                donor not in imputed_cells for donor in donor_by_cell.values()
            ),
            "late_emerging_cell_count_6": len(future_counts) == 6,
            "solar_overlap_1113": len(overlap) == 1_113,
            "solar_current_44_equals_old_minus_wind": solar_current == solar_only,
            "v2_qa_passed": v2_qa.get("status") == "passed",
            "v2_raw_compressed_307": v2_qa.get("raw_factor_compressed_rows") == 307,
            "v2_filled_compressed_308": v2_qa.get("filled_factor_compressed_rows") == 308,
        }
    )

    same_state = sum(
        state_by_cell[cell_id] == state_by_cell[donor_by_cell[cell_id]]
        for cell_id in imputed_cells
    )
    bands = Counter(
        "<=30"
        if value <= 30
        else "30-60"
        if value <= 60
        else "60-100"
        if value <= 100
        else ">100"
        for value in unique_distances
    )
    report = {
        "status": "passed" if all(checks.values()) else "failed",
        "created_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "inputs": {
            "raw_v1": {"file": args.raw_v1.name, "sha256": sha256(args.raw_v1)},
            "filled_v1": {"file": args.filled_v1.name, "sha256": sha256(args.filled_v1)},
            "filled_v2": {"file": args.filled_v2.name, "sha256": sha256(args.filled_v2)},
        },
        "grain": {
            "rows": filled.num_rows,
            "canonical_cells": len(set(cell_ids)),
            "scenarios": sorted(set(scenarios)),
            "horizons": sorted(set(horizons)),
        },
        "availability": {
            "metric_eligible_cells": manifest["metric_eligible_cell_count"],
            "imputed_cells": len(imputed_cells),
            "raw_factor_null_rows": sum(value is None for value in raw_factors),
            "filled_factor_null_rows": sum(value is None for value in filled_factors),
        },
        "donors": {
            "distance_km": {
                "min": min(unique_distances),
                "median": percentile(unique_distances, 0.5),
                "p95": percentile(unique_distances, 0.95),
                "max": max(unique_distances),
            },
            "distance_bands": dict(sorted(bands.items())),
            "same_state_count": same_state,
            "same_state_share": same_state / len(imputed_cells),
        },
        "late_emerging": {
            "cell_count": len(future_counts),
            "row_count": len(late_rows),
            "rows_by_cell_and_scenario": {
                str(cell_id): dict(sorted(counts.items()))
                for cell_id, counts in sorted(future_counts.items())
            },
        },
        "solar_pattern_comparison": {
            "older_solar_missing_cells": len(solar_old),
            "wind_unavailable_cells": len(imputed_cells),
            "overlap_cells": len(overlap),
            "overlap_share_of_wind": len(overlap) / len(imputed_cells),
            "wind_only_cells": sorted(wind_only),
            "solar_only_cells": len(solar_only),
            "current_solar_missing_equals_solar_only": solar_current == solar_only,
        },
        "stabilization": {
            "raw_compressed_rows": v2_qa["raw_factor_compressed_rows"],
            "filled_compressed_rows": v2_qa["filled_factor_compressed_rows"],
            "additional_imputed_compressed_rows": len(imputed_compressed_rows),
            "candidate_range": v2_qa["filled_candidate_range"],
        },
        "checks": checks,
    }
    if report["status"] != "passed":
        failed = [name for name, passed in checks.items() if not passed]
        raise ValueError(f"Nearest-fill validation failed: {failed}")

    (args.output_dir / "nearest_fill_validation.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    write_csv(args.output_dir / "nearest_fill_longest_donors.csv", longest)
    write_csv(args.output_dir / "nearest_fill_late_emerging_rows.csv", late_rows)
    write_csv(
        args.output_dir / "nearest_fill_imputed_compression_rows.csv",
        imputed_compressed_rows,
    )
    print(json.dumps({
        "status": report["status"],
        "imputed_cells": len(imputed_cells),
        "raw_null_rows": report["availability"]["raw_factor_null_rows"],
        "filled_null_rows": report["availability"]["filled_factor_null_rows"],
        "same_state_share": report["donors"]["same_state_share"],
        "late_emerging_cells": len(future_counts),
        "solar_overlap_cells": len(overlap),
        "filled_compressed_rows": v2_qa["filled_factor_compressed_rows"],
    }))


if __name__ == "__main__":
    main()

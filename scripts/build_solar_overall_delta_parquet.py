#!/usr/bin/env python3
"""Build the canonical Solar SCR overall physical-damage delta Parquet.

Input workbook values are supplied as JSON shards emitted by
notebooks/conus_solar_physical_delta/support/extract_overall_damage.mjs.
Missing source cells are filled from the geographically nearest observed
canonical grid cell while raw fields remain null.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import math
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
from scipy.spatial import cKDTree


SCENARIOS = ("ssp2-4.5", "ssp5-8.5")
HORIZONS = tuple(range(2025, 2101, 5))
BASELINE_YEAR = 2025
EARTH_RADIUS_KM = 6371.0088
SCHEMA_VERSION = "scr_solar_overall_delta_v1"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--grid", required=True, type=Path)
    parser.add_argument("--shards", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_grid(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    grid = []
    for row in rows:
        grid.append(
            {
                "cell_id": int(row["cell_id"]),
                "lat_idx": int(row["lat_idx"]),
                "lon_idx": int(row["lon_idx"]),
                "lat_center": float(row["lat_center"]),
                "lon_center": float(row["lon_center"]),
                "state_abbr": row["state_abbr"],
            }
        )
    ids = [row["cell_id"] for row in grid]
    if len(ids) != len(set(ids)):
        raise ValueError("Canonical grid contains duplicate cell_id values.")
    return sorted(grid, key=lambda row: row["cell_id"])


def load_observed(shard_dir: Path) -> dict[int, dict]:
    observed: dict[int, dict] = {}
    shard_paths = sorted(shard_dir.rglob("*.json"))
    if not shard_paths:
        raise ValueError(f"No JSON shards found under {shard_dir}")
    errors = []
    for shard_path in shard_paths:
        payload = json.loads(shard_path.read_text(encoding="utf-8"))
        for item in payload["files"]:
            if item["status"] != "ok":
                errors.append({"shard": str(shard_path), **item})
                continue
            cell_id = int(item["cellId"])
            if cell_id in observed:
                raise ValueError(f"Duplicate observed workbook for cell {cell_id}")
            observed[cell_id] = item
    if errors:
        raise ValueError(f"Workbook extraction contains {len(errors)} errors.")
    return observed


def xyz(lat: float, lon: float) -> tuple[float, float, float]:
    lat_rad = math.radians(lat)
    lon_rad = math.radians(lon)
    cos_lat = math.cos(lat_rad)
    return (
        cos_lat * math.cos(lon_rad),
        cos_lat * math.sin(lon_rad),
        math.sin(lat_rad),
    )


def haversine_km(a: dict, b: dict) -> float:
    lat1, lon1 = math.radians(a["lat_center"]), math.radians(a["lon_center"])
    lat2, lon2 = math.radians(b["lat_center"]), math.radians(b["lon_center"])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    value = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return EARTH_RADIUS_KM * 2 * math.asin(min(1.0, math.sqrt(value)))


def nearest_donors(grid: list[dict], observed_ids: set[int]) -> dict[int, tuple[int, float]]:
    by_id = {row["cell_id"]: row for row in grid}
    donor_rows = [row for row in grid if row["cell_id"] in observed_ids]
    donor_xyz = [xyz(row["lat_center"], row["lon_center"]) for row in donor_rows]
    tree = cKDTree(donor_xyz)
    result: dict[int, tuple[int, float]] = {}
    k = min(16, len(donor_rows))
    for target in grid:
        if target["cell_id"] in observed_ids:
            result[target["cell_id"]] = (target["cell_id"], 0.0)
            continue
        _, candidates = tree.query(xyz(target["lat_center"], target["lon_center"]), k=k)
        if k == 1:
            candidates = [int(candidates)]
        ranked = []
        for candidate_index in candidates:
            donor = donor_rows[int(candidate_index)]
            ranked.append((haversine_km(target, donor), donor["cell_id"]))
        distance, donor_id = min(ranked, key=lambda item: (round(item[0], 9), item[1]))
        if donor_id not in by_id:
            raise AssertionError("Nearest donor is not canonical.")
        result[target["cell_id"]] = (donor_id, distance)
    return result


def value_for(item: dict, scenario: str, horizon: int) -> float:
    value = item["totals"].get(scenario, {}).get(str(horizon))
    if value is None:
        raise ValueError(f"Missing {scenario}/{horizon} total for cell {item['cellId']}")
    return float(value)


def build_columns(grid: list[dict], observed: dict[int, dict], donors: dict[int, tuple[int, float]]):
    columns = {
        name: []
        for name in (
            "cell_id", "lat_idx", "lon_idx", "lat_center", "lon_center", "state_abbr",
            "asset_type", "ticcs_subclass", "scenario", "baseline_year", "horizon",
            "years_from_baseline", "scr_metric_name", "baseline_damage_raw",
            "future_damage_raw", "baseline_damage_magnitude_raw",
            "future_damage_magnitude_raw", "absolute_change_magnitude_raw",
            "factor_raw", "percent_change_raw", "baseline_damage_filled",
            "future_damage_filled", "baseline_damage_magnitude_filled",
            "future_damage_magnitude_filled", "absolute_change_magnitude_filled",
            "factor_filled", "percent_change_filled", "is_imputed", "fill_method", "source_cell_id",
            "donor_distance_km", "source_uri", "quality_status", "schema_version",
        )
    }
    for cell in grid:
        target_id = cell["cell_id"]
        is_observed = target_id in observed
        donor_id, distance = donors[target_id]
        source = observed[donor_id]
        raw = observed.get(target_id)
        for scenario in SCENARIOS:
            donor_baseline_signed = value_for(source, scenario, BASELINE_YEAR)
            donor_baseline_magnitude = abs(donor_baseline_signed)
            if donor_baseline_magnitude == 0:
                raise ValueError(f"Zero baseline for donor cell {donor_id}, {scenario}")
            raw_baseline_signed = value_for(raw, scenario, BASELINE_YEAR) if raw else None
            raw_baseline_magnitude = abs(raw_baseline_signed) if raw else None
            if raw_baseline_magnitude == 0:
                raise ValueError(f"Zero baseline for observed cell {target_id}, {scenario}")
            for horizon in HORIZONS:
                donor_future_signed = value_for(source, scenario, horizon)
                donor_future_magnitude = abs(donor_future_signed)
                factor_filled = donor_future_magnitude / donor_baseline_magnitude
                raw_future_signed = value_for(raw, scenario, horizon) if raw else None
                raw_future_magnitude = abs(raw_future_signed) if raw else None
                factor_raw = raw_future_magnitude / raw_baseline_magnitude if raw else None
                values = {
                    "cell_id": target_id,
                    "lat_idx": cell["lat_idx"],
                    "lon_idx": cell["lon_idx"],
                    "lat_center": cell["lat_center"],
                    "lon_center": cell["lon_center"],
                    "state_abbr": cell["state_abbr"],
                    "asset_type": "SolarPV",
                    "ticcs_subclass": "IC702010",
                    "scenario": scenario,
                    "baseline_year": BASELINE_YEAR,
                    "horizon": horizon,
                    "years_from_baseline": horizon - BASELINE_YEAR,
                    "scr_metric_name": "adjustedTotalDamage",
                    "baseline_damage_raw": raw_baseline_signed,
                    "future_damage_raw": raw_future_signed,
                    "baseline_damage_magnitude_raw": raw_baseline_magnitude,
                    "future_damage_magnitude_raw": raw_future_magnitude,
                    "absolute_change_magnitude_raw": (
                        raw_future_magnitude - raw_baseline_magnitude if raw else None
                    ),
                    "factor_raw": factor_raw,
                    "percent_change_raw": factor_raw - 1 if factor_raw is not None else None,
                    "baseline_damage_filled": donor_baseline_signed,
                    "future_damage_filled": donor_future_signed,
                    "baseline_damage_magnitude_filled": donor_baseline_magnitude,
                    "future_damage_magnitude_filled": donor_future_magnitude,
                    "absolute_change_magnitude_filled": donor_future_magnitude - donor_baseline_magnitude,
                    "factor_filled": factor_filled,
                    "percent_change_filled": factor_filled - 1,
                    "is_imputed": not is_observed,
                    "fill_method": "observed" if is_observed else "nearest_observed_cell",
                    "source_cell_id": donor_id,
                    "donor_distance_km": distance,
                    "source_uri": f"gs://infrasure-scr-data/physical_risks_exports/{source['filename']}",
                    "quality_status": "observed" if is_observed else "imputed_nearest",
                    "schema_version": SCHEMA_VERSION,
                }
                for name, value in values.items():
                    columns[name].append(value)
    return columns


def percentile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    index = (len(ordered) - 1) * q
    lower, upper = math.floor(index), math.ceil(index)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] * (upper - index) + ordered[upper] * (index - lower)


def main() -> None:
    args = parse_args()
    grid = load_grid(args.grid)
    observed = load_observed(args.shards)
    grid_ids = {row["cell_id"] for row in grid}
    extra = sorted(set(observed) - grid_ids)
    if extra:
        raise ValueError(f"Observed source includes {len(extra)} noncanonical cells.")
    missing = sorted(grid_ids - set(observed))
    donors = nearest_donors(grid, set(observed))
    columns = build_columns(grid, observed, donors)

    schema = pa.schema(
        [
            ("cell_id", pa.int32()), ("lat_idx", pa.int16()), ("lon_idx", pa.int16()),
            ("lat_center", pa.float64()), ("lon_center", pa.float64()), ("state_abbr", pa.string()),
            ("asset_type", pa.string()), ("ticcs_subclass", pa.string()), ("scenario", pa.string()),
            ("baseline_year", pa.int16()), ("horizon", pa.int16()), ("years_from_baseline", pa.int16()),
            ("scr_metric_name", pa.string()), ("baseline_damage_raw", pa.float64()),
            ("future_damage_raw", pa.float64()), ("baseline_damage_magnitude_raw", pa.float64()),
            ("future_damage_magnitude_raw", pa.float64()), ("absolute_change_magnitude_raw", pa.float64()),
            ("factor_raw", pa.float64()), ("percent_change_raw", pa.float64()),
            ("baseline_damage_filled", pa.float64()), ("future_damage_filled", pa.float64()),
            ("baseline_damage_magnitude_filled", pa.float64()),
            ("future_damage_magnitude_filled", pa.float64()),
            ("absolute_change_magnitude_filled", pa.float64()), ("factor_filled", pa.float64()),
            ("percent_change_filled", pa.float64()), ("is_imputed", pa.bool_()),
            ("fill_method", pa.string()), ("source_cell_id", pa.int32()),
            ("donor_distance_km", pa.float64()), ("source_uri", pa.string()),
            ("quality_status", pa.string()), ("schema_version", pa.string()),
        ],
        metadata={
            b"schema_version": SCHEMA_VERSION.encode(),
            b"factor_definition": b"abs(future adjustedTotalDamage) / abs(2025 adjustedTotalDamage)",
            b"missing_cell_method": b"nearest observed canonical cell by great-circle distance",
            b"canonical_grid_sha256": sha256(args.grid).encode(),
        },
    )
    table = pa.Table.from_pydict(columns, schema=schema)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, args.output, compression="zstd", row_group_size=32768)

    expected_rows = len(grid) * len(SCENARIOS) * len(HORIZONS)
    if table.num_rows != expected_rows:
        raise AssertionError(f"Expected {expected_rows} rows, got {table.num_rows}")
    if table.column("factor_filled").null_count:
        raise AssertionError("factor_filled contains nulls")
    expected_raw_nulls = len(missing) * len(SCENARIOS) * len(HORIZONS)
    if table.column("factor_raw").null_count != expected_raw_nulls:
        raise AssertionError("factor_raw null count does not reconcile to absent cells")
    distances = [donors[cell_id][1] for cell_id in missing]
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "created_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "output_file": args.output.name,
        "output_sha256": sha256(args.output),
        "output_size_bytes": args.output.stat().st_size,
        "canonical_grid": str(args.grid),
        "canonical_grid_sha256": sha256(args.grid),
        "source_bucket": "gs://infrasure-scr-data/physical_risks_exports/",
        "asset_type": "SolarPV",
        "ticcs_subclass": "IC702010",
        "metric": "adjustedTotalDamage",
        "factor_definition": "abs(future) / abs(2025 baseline), within scenario",
        "scenarios": list(SCENARIOS),
        "horizons": list(HORIZONS),
        "row_count": table.num_rows,
        "canonical_cell_count": len(grid),
        "observed_cell_count": len(observed),
        "imputed_cell_count": len(missing),
        "factor_raw_null_count": table.column("factor_raw").null_count,
        "factor_filled_null_count": table.column("factor_filled").null_count,
        "missing_cell_method": "nearest_observed_cell",
        "donor_distance_km": {
            "min": min(distances),
            "median": percentile(distances, 0.5),
            "p95": percentile(distances, 0.95),
            "max": max(distances),
        },
        "iso_rto_included": False,
        "checks": {
            "expected_rows": expected_rows,
            "all_filled_factors_present": True,
            "raw_nulls_match_imputed_rows": True,
            "observed_source_errors": 0,
            "noncanonical_observed_cells": 0,
        },
    }
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()

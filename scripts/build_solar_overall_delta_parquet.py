#!/usr/bin/env python3
"""Build a canonical SCR overall physical-damage delta Parquet.

Input workbook values are supplied as JSON shards emitted by
notebooks/conus_solar_physical_delta/support/extract_overall_damage.mjs.
The historical Solar CLI remains the default. Asset identity, source prefix,
schema version, and missing-cell policy can be supplied explicitly for another
asset class such as Onshore Wind.
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
DEFAULT_SCHEMA_VERSION = "scr_solar_overall_delta_v1"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--grid", required=True, type=Path)
    parser.add_argument(
        "--grid-label",
        help="Stable URI or release label to record instead of the local grid path.",
    )
    parser.add_argument("--shards", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--asset-type", default="SolarPV")
    parser.add_argument("--ticcs-subclass", default="IC702010")
    parser.add_argument(
        "--source-prefix",
        default="gs://infrasure-scr-data/physical_risks_exports/",
    )
    parser.add_argument("--schema-version", default=DEFAULT_SCHEMA_VERSION)
    parser.add_argument(
        "--lineage-manifest",
        type=Path,
        help=(
            "Optional prior manifest from the same immutable extraction. "
            "When supplied, source/grid/count parity is validated and recorded."
        ),
    )
    parser.add_argument(
        "--lineage-label",
        help="Stable URI or release label to record instead of the local lineage path.",
    )
    parser.add_argument(
        "--missing-policy",
        choices=("nearest_observed_cell", "retain_null", "error"),
        default="nearest_observed_cell",
    )
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


def optional_value(item: dict | None, scenario: str, horizon: int) -> float | None:
    if item is None:
        return None
    value = item["totals"].get(scenario, {}).get(str(horizon))
    return None if value is None else float(value)


def has_complete_factor_path(item: dict) -> bool:
    for scenario in SCENARIOS:
        baseline = optional_value(item, scenario, BASELINE_YEAR)
        if baseline is None or abs(baseline) == 0:
            return False
        if any(optional_value(item, scenario, horizon) is None for horizon in HORIZONS):
            return False
    return True


def build_columns(
    grid: list[dict],
    observed: dict[int, dict],
    donors: dict[int, tuple[int, float]],
    *,
    asset_type: str,
    ticcs_subclass: str,
    source_prefix: str,
    schema_version: str,
    metric_eligible_ids: set[int],
):
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
        has_workbook = target_id in observed
        has_metric = target_id in metric_eligible_ids
        donor_id, distance = donors.get(target_id, (None, None))
        source = observed.get(donor_id) if donor_id is not None else None
        raw = observed.get(target_id)
        for scenario in SCENARIOS:
            donor_baseline_signed = optional_value(source, scenario, BASELINE_YEAR)
            donor_baseline_magnitude = (
                abs(donor_baseline_signed) if donor_baseline_signed is not None else None
            )
            raw_baseline_signed = optional_value(raw, scenario, BASELINE_YEAR)
            raw_baseline_magnitude = (
                abs(raw_baseline_signed) if raw_baseline_signed is not None else None
            )
            for horizon in HORIZONS:
                donor_future_signed = optional_value(source, scenario, horizon)
                donor_future_magnitude = (
                    abs(donor_future_signed) if donor_future_signed is not None else None
                )
                factor_filled = (
                    donor_future_magnitude / donor_baseline_magnitude
                    if donor_future_magnitude is not None
                    and donor_baseline_magnitude is not None
                    and donor_baseline_magnitude > 0
                    else None
                )
                raw_future_signed = optional_value(raw, scenario, horizon)
                raw_future_magnitude = (
                    abs(raw_future_signed) if raw_future_signed is not None else None
                )
                factor_raw = (
                    raw_future_magnitude / raw_baseline_magnitude
                    if raw_future_magnitude is not None
                    and raw_baseline_magnitude is not None
                    and raw_baseline_magnitude > 0
                    else None
                )
                is_imputed = donor_id is not None and donor_id != target_id
                if has_metric:
                    quality_status = "observed"
                    fill_method = "observed"
                elif donor_id is not None:
                    quality_status = (
                        "imputed_metric_unavailable_nearest"
                        if has_workbook
                        else "imputed_nearest"
                    )
                    fill_method = "nearest_observed_cell"
                else:
                    quality_status = "metric_unavailable" if has_workbook else "missing_source"
                    fill_method = "not_filled"
                values = {
                    "cell_id": target_id,
                    "lat_idx": cell["lat_idx"],
                    "lon_idx": cell["lon_idx"],
                    "lat_center": cell["lat_center"],
                    "lon_center": cell["lon_center"],
                    "state_abbr": cell["state_abbr"],
                    "asset_type": asset_type,
                    "ticcs_subclass": ticcs_subclass,
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
                        raw_future_magnitude - raw_baseline_magnitude
                        if raw_future_magnitude is not None and raw_baseline_magnitude is not None
                        else None
                    ),
                    "factor_raw": factor_raw,
                    "percent_change_raw": factor_raw - 1 if factor_raw is not None else None,
                    "baseline_damage_filled": donor_baseline_signed,
                    "future_damage_filled": donor_future_signed,
                    "baseline_damage_magnitude_filled": donor_baseline_magnitude,
                    "future_damage_magnitude_filled": donor_future_magnitude,
                    "absolute_change_magnitude_filled": (
                        donor_future_magnitude - donor_baseline_magnitude
                        if donor_future_magnitude is not None
                        and donor_baseline_magnitude is not None
                        else None
                    ),
                    "factor_filled": factor_filled,
                    "percent_change_filled": (
                        factor_filled - 1 if factor_filled is not None else None
                    ),
                    "is_imputed": is_imputed,
                    "fill_method": fill_method,
                    "source_cell_id": donor_id,
                    "donor_distance_km": distance,
                    "source_uri": (
                        f"{source_prefix.rstrip('/')}/{raw['filename']}"
                        if raw is not None
                        else (
                            f"{source_prefix.rstrip('/')}/{source['filename']}"
                            if source is not None
                            else None
                        )
                    ),
                    "quality_status": quality_status,
                    "schema_version": schema_version,
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
    missing_source = sorted(grid_ids - set(observed))
    metric_eligible_ids = {
        cell_id for cell_id, item in observed.items() if has_complete_factor_path(item)
    }
    metric_unavailable = sorted(set(observed) - metric_eligible_ids)
    unavailable = sorted(grid_ids - metric_eligible_ids)
    lineage = None
    if args.lineage_manifest is not None:
        lineage = json.loads(args.lineage_manifest.read_text(encoding="utf-8"))
        expected = {
            "canonical_grid_sha256": sha256(args.grid),
            "source_bucket": args.source_prefix,
            "asset_type": args.asset_type,
            "ticcs_subclass": args.ticcs_subclass,
            "canonical_cell_count": len(grid),
            "observed_cell_count": len(observed),
            "metric_eligible_cell_count": len(metric_eligible_ids),
            "metric_unavailable_cell_count": len(metric_unavailable),
            "missing_source_cell_count": len(missing_source),
        }
        mismatches = {
            key: {"expected": value, "lineage": lineage.get(key)}
            for key, value in expected.items()
            if lineage.get(key) != value
        }
        if mismatches:
            raise ValueError(f"Lineage manifest does not match extraction: {mismatches}")
    if unavailable and args.missing_policy == "error":
        raise ValueError(
            "Missing-policy=error but "
            f"{len(missing_source)} cells have no workbook and "
            f"{len(metric_unavailable)} observed workbooks lack a complete factor path."
        )
    if args.missing_policy == "nearest_observed_cell":
        donors = nearest_donors(grid, metric_eligible_ids)
    else:
        donors = {
            cell_id: (cell_id, 0.0)
            for cell_id in metric_eligible_ids
        }
    columns = build_columns(
        grid,
        observed,
        donors,
        asset_type=args.asset_type,
        ticcs_subclass=args.ticcs_subclass,
        source_prefix=args.source_prefix,
        schema_version=args.schema_version,
        metric_eligible_ids=metric_eligible_ids,
    )

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
            b"schema_version": args.schema_version.encode(),
            b"factor_definition": b"abs(future adjustedTotalDamage) / abs(2025 adjustedTotalDamage)",
            b"missing_cell_method": (
                b"nearest observed canonical cell by great-circle distance"
                if args.missing_policy == "nearest_observed_cell"
                else args.missing_policy.encode()
            ),
            b"canonical_grid_sha256": sha256(args.grid).encode(),
        },
    )
    table = pa.Table.from_pydict(columns, schema=schema)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, args.output, compression="zstd", row_group_size=32768)

    expected_rows = len(grid) * len(SCENARIOS) * len(HORIZONS)
    if table.num_rows != expected_rows:
        raise AssertionError(f"Expected {expected_rows} rows, got {table.num_rows}")
    if args.missing_policy != "retain_null" and table.column("factor_filled").null_count:
        raise AssertionError("factor_filled contains nulls")
    expected_raw_nulls = 0
    for cell in grid:
        item = observed.get(cell["cell_id"])
        for scenario in SCENARIOS:
            baseline = optional_value(item, scenario, BASELINE_YEAR)
            for horizon in HORIZONS:
                future = optional_value(item, scenario, horizon)
                if baseline is None or abs(baseline) == 0 or future is None:
                    expected_raw_nulls += 1
    if table.column("factor_raw").null_count != expected_raw_nulls:
        raise AssertionError("factor_raw null count does not reconcile to unavailable factor paths")
    imputed_ids = [
        cell_id
        for cell_id in unavailable
        if cell_id in donors and donors[cell_id][0] != cell_id
    ]
    distances = [donors[cell_id][1] for cell_id in imputed_ids]
    distance_summary = (
        {
            "min": min(distances),
            "median": percentile(distances, 0.5),
            "p95": percentile(distances, 0.95),
            "max": max(distances),
        }
        if distances
        else {"min": None, "median": None, "p95": None, "max": None}
    )
    manifest = {
        "schema_version": args.schema_version,
        "created_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "output_file": args.output.name,
        "output_sha256": sha256(args.output),
        "output_size_bytes": args.output.stat().st_size,
        "canonical_grid": args.grid_label or str(args.grid),
        "canonical_grid_sha256": sha256(args.grid),
        "source_bucket": args.source_prefix,
        "asset_type": args.asset_type,
        "ticcs_subclass": args.ticcs_subclass,
        "metric": "adjustedTotalDamage",
        "factor_definition": "abs(future) / abs(2025 baseline), within scenario",
        "scenarios": list(SCENARIOS),
        "horizons": list(HORIZONS),
        "row_count": table.num_rows,
        "canonical_cell_count": len(grid),
        "observed_cell_count": len(observed),
        "metric_eligible_cell_count": len(metric_eligible_ids),
        "metric_unavailable_cell_count": len(metric_unavailable),
        "missing_source_cell_count": len(missing_source),
        "imputed_cell_count": len(imputed_ids),
        "factor_raw_null_count": table.column("factor_raw").null_count,
        "factor_filled_null_count": table.column("factor_filled").null_count,
        "missing_cell_method": args.missing_policy,
        "donor_distance_km": distance_summary,
        "iso_rto_included": False,
        "checks": {
            "expected_rows": expected_rows,
            "all_filled_factors_present": table.column("factor_filled").null_count == 0,
            "raw_nulls_match_unavailable_factor_paths": True,
            "observed_source_errors": 0,
            "noncanonical_observed_cells": 0,
        },
    }
    if lineage is not None:
        manifest["checks"]["source_lineage_matches"] = True
        manifest["source_lineage"] = {
            "manifest_file": args.lineage_label or str(args.lineage_manifest),
            "manifest_sha256": sha256(args.lineage_manifest),
            "schema_version": lineage.get("schema_version"),
            "output_sha256": lineage.get("output_sha256"),
            "publication_prefix": lineage.get("publication_prefix"),
            "cloud_run": lineage.get("cloud_run"),
        }
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()

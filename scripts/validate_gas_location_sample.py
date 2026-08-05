#!/usr/bin/env python3
"""Validate the 146-location SCR gas reference sample.

The script reads the CSV exports directly from the source ZIP, checks their
grain and internal arithmetic, derives baseline-to-future change factors, and
optionally verifies that each submitted coordinate is the center of its source
grid cell. It uses only the Python standard library so the checks can run in a
clean environment.
"""

from __future__ import annotations

import argparse
import csv
import html
import io
import json
import math
import re
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from zipfile import ZipFile


SCENARIOS = ("ssp2-4.5", "ssp5-8.5")
FACTOR_HORIZONS = ("2050", "2100")
TOTAL_METRICS = (
    "adjustedTotalDamage",
    "adjustedTotalDisruption",
    "adjustedTotalDisruptionDamageEquivalent",
    "adjustedTotalValueImpact",
)
RAW_ADJUSTED_PAIRS = (
    ("hazardDamage", "adjustedHazardDamage"),
    ("hazardDisruption", "adjustedHazardDisruption"),
    ("hazardDisruptionDamageEquivalent", "adjustedHazardDisruptionDamageEquivalent"),
    ("hazardValueImpact", "adjustedHazardValueImpact"),
    ("totalDamage", "adjustedTotalDamage"),
    ("totalDisruption", "adjustedTotalDisruption"),
    ("totalDisruptionDamageEquivalent", "adjustedTotalDisruptionDamageEquivalent"),
    ("totalValueImpact", "adjustedTotalValueImpact"),
)


def number(value: str | None) -> float | None:
    if value is None or not value.strip():
        return None
    return float(value)


def summarize(values: list[float]) -> dict[str, float | int | None]:
    if not values:
        return {"n": 0, "min": None, "median": None, "max": None}
    return {
        "n": len(values),
        "min": min(values),
        "median": statistics.median(values),
        "max": max(values),
    }


def factor_directions(values: list[float]) -> dict[str, int]:
    return {
        "below_1x": sum(value < 1.0 - 1e-12 for value in values),
        "equal_1x": sum(math.isclose(value, 1.0, rel_tol=0, abs_tol=1e-12) for value in values),
        "above_1x": sum(value > 1.0 + 1e-12 for value in values),
    }


def parse_coordinates(value: str) -> tuple[float, float]:
    match = re.fullmatch(r"\(\s*([-+0-9.eE]+)\s*,\s*([-+0-9.eE]+)\s*\)", value)
    if not match:
        raise ValueError(f"Unexpected coordinate format: {value!r}")
    return float(match.group(1)), float(match.group(2))


def read_grid(path: Path | None) -> dict[str, dict[str, str]]:
    if path is None:
        return {}
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return {row["cell_id"]: row for row in csv.DictReader(handle)}


def read_workbook_inputs(workbook_bytes: bytes) -> dict[str, object]:
    """Read the small input block from the XLSX ReadMe sheet."""
    with ZipFile(io.BytesIO(workbook_bytes)) as workbook:
        sheet_xml = workbook.read("xl/worksheets/sheet1.xml").decode("utf-8")
    cells: dict[str, str] = {}
    for match in re.finditer(r'<c\s+[^>]*r="([A-Z]+[0-9]+)"[^>]*>(.*?)</c>', sheet_xml):
        reference, body = match.groups()
        inline = re.search(r"<t(?:\s[^>]*)?>(.*?)</t>", body, flags=re.DOTALL)
        numeric = re.search(r"<v>(.*?)</v>", body, flags=re.DOTALL)
        if inline:
            cells[reference] = html.unescape(inline.group(1))
        elif numeric:
            cells[reference] = html.unescape(numeric.group(1))
    return {
        "asset_type": cells.get("B5"),
        "asset_value": number(cells.get("B7")),
        "asset_revenue": number(cells.get("B8")),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--zip", dest="zip_path", type=Path, required=True)
    parser.add_argument("--grid", dest="grid_path", type=Path)
    parser.add_argument("--output", dest="output_path", type=Path, required=True)
    parser.add_argument("--manifest-output", dest="manifest_path", type=Path)
    args = parser.parse_args()

    grid = read_grid(args.grid_path)
    reports: list[dict[str, object]] = []
    archive_stems: dict[str, set[str]] = defaultdict(set)

    with ZipFile(args.zip_path) as archive:
        members = [name for name in archive.namelist() if not name.endswith("/")]
        for name in members:
            suffix = Path(name).suffix.lower()
            if suffix in {".csv", ".xlsx"}:
                archive_stems[str(Path(name).with_suffix(""))].add(suffix)

        csv_members = sorted(name for name in members if name.lower().endswith(".csv"))
        for name in csv_members:
            with archive.open(name) as raw:
                reader = csv.DictReader(io.TextIOWrapper(raw, encoding="utf-8-sig", newline=""))
                rows = list(reader)
                columns = reader.fieldnames or []
            if not rows:
                raise ValueError(f"Empty CSV: {name}")

            first = rows[0]
            match = re.search(r"Cell_(\d+)", first["assetName"])
            if not match:
                raise ValueError(f"Could not find cell ID in {first['assetName']!r}")
            cell_id = match.group(1)
            lat, lon = parse_coordinates(first["geolocationCoordinates"])
            xlsx_name = str(Path(name).with_suffix(".xlsx"))
            workbook_inputs = (
                read_workbook_inputs(archive.read(xlsx_name)) if xlsx_name in members else {}
            )

            by_total: dict[tuple[str, str, str], set[float]] = defaultdict(set)
            by_hazard: dict[tuple[str, str, str, str], set[float]] = defaultdict(set)
            for row in rows:
                scenario = row["scenario"]
                horizon = row["timeHorizon"]
                for metric in TOTAL_METRICS:
                    value = number(row.get(metric))
                    if value is not None:
                        by_total[(scenario, horizon, metric)].add(value)
                hazard_damage = number(row.get("adjustedHazardDamage"))
                if hazard_damage is not None:
                    by_hazard[(scenario, horizon, row["hazard"], "adjustedHazardDamage")].add(
                        hazard_damage
                    )

            inconsistent_totals = [
                [*key, sorted(values)] for key, values in by_total.items() if len(values) != 1
            ]
            inconsistent_hazards = [
                [*key, sorted(values)] for key, values in by_hazard.items() if len(values) != 1
            ]

            reports.append(
                {
                    "archive_member": name,
                    "cell_id": cell_id,
                    "asset_id": first["assetId"],
                    "asset_name": first["assetName"],
                    "coordinates": [lat, lon],
                    "report_date": first["reportDate"],
                    "ticcs_subclass": first["ticcsSubClass"],
                    "ticcs_subclass_name": first["ticcsSubClassName"],
                    "workbook_inputs": workbook_inputs,
                    "row_count": len(rows),
                    "columns": columns,
                    "rows": rows,
                    "totals": by_total,
                    "hazard_damage": by_hazard,
                    "inconsistent_totals": inconsistent_totals,
                    "inconsistent_hazards": inconsistent_hazards,
                }
            )

    hazards = sorted({row["hazard"] for report in reports for row in report["rows"]})
    hazard_coverage: dict[str, dict[str, object]] = {}
    hazard_factor_summaries: dict[str, dict[str, object]] = {}
    for hazard in hazards:
        files_present = 0
        indicator_value_files = 0
        indicator_rating_files = 0
        hazard_rating_files = 0
        any_damage_files = 0
        usable_2050_files = 0
        usable_2100_files = 0
        indicators: set[str] = set()
        for report in reports:
            rows = [row for row in report["rows"] if row["hazard"] == hazard]
            if not rows:
                continue
            files_present += 1
            indicators.update(row["indicator"] for row in rows)
            indicator_value_files += any(number(row.get("indicatorValue")) is not None for row in rows)
            indicator_rating_files += any(bool(row.get("indicatorRating")) for row in rows)
            hazard_rating_files += any(bool(row.get("HazardRating")) for row in rows)
            any_damage_files += any(number(row.get("adjustedHazardDamage")) is not None for row in rows)

            for future, counter_name in (("2050", "usable_2050"), ("2100", "usable_2100")):
                usable = False
                for scenario in SCENARIOS:
                    baseline = report["hazard_damage"].get(
                        (scenario, "2025", hazard, "adjustedHazardDamage")
                    )
                    projected = report["hazard_damage"].get(
                        (scenario, future, hazard, "adjustedHazardDamage")
                    )
                    if (
                        baseline
                        and projected
                        and len(baseline) == 1
                        and len(projected) == 1
                        and next(iter(baseline)) != 0
                    ):
                        usable = True
                        break
                if usable and counter_name == "usable_2050":
                    usable_2050_files += 1
                if usable and counter_name == "usable_2100":
                    usable_2100_files += 1

        hazard_coverage[hazard] = {
            "files_present": files_present,
            "indicator_value_files": indicator_value_files,
            "indicator_rating_files": indicator_rating_files,
            "hazard_rating_files": hazard_rating_files,
            "any_adjusted_hazard_damage_files": any_damage_files,
            "usable_2050_factor_files": usable_2050_files,
            "usable_2100_factor_files": usable_2100_files,
            "indicators": sorted(indicators),
        }

        hazard_factor_summaries[hazard] = {}
        for scenario in SCENARIOS:
            scenario_results: dict[str, object] = {}
            for future in FACTOR_HORIZONS:
                baseline_present = 0
                future_present = 0
                factors: list[float] = []
                unchanged = 0
                for report in reports:
                    baseline_set = report["hazard_damage"].get(
                        (scenario, "2025", hazard, "adjustedHazardDamage")
                    )
                    future_set = report["hazard_damage"].get(
                        (scenario, future, hazard, "adjustedHazardDamage")
                    )
                    baseline = (
                        next(iter(baseline_set))
                        if baseline_set and len(baseline_set) == 1
                        else None
                    )
                    projected = (
                        next(iter(future_set)) if future_set and len(future_set) == 1 else None
                    )
                    baseline_present += baseline is not None
                    future_present += projected is not None
                    if baseline not in (None, 0) and projected is not None:
                        factor = projected / baseline
                        factors.append(factor)
                        unchanged += math.isclose(factor, 1.0, rel_tol=0, abs_tol=1e-12)
                scenario_results[future] = {
                    "baseline_present": baseline_present,
                    "future_present": future_present,
                    "factor_summary": summarize(factors),
                    "factor_direction_counts": factor_directions(factors),
                    "unchanged_factor_count": unchanged,
                }
            hazard_factor_summaries[hazard][scenario] = scenario_results

    total_coverage: dict[str, dict[str, object]] = {}
    for metric in TOTAL_METRICS:
        total_coverage[metric] = {}
        for scenario in SCENARIOS:
            baseline_present = 0
            baseline_nonzero = 0
            future_results: dict[str, object] = {}
            for future in FACTOR_HORIZONS:
                factors: list[float] = []
                unchanged = 0
                future_present = 0
                for report in reports:
                    baseline_set = report["totals"].get((scenario, "2025", metric))
                    future_set = report["totals"].get((scenario, future, metric))
                    baseline = next(iter(baseline_set)) if baseline_set and len(baseline_set) == 1 else None
                    projected = next(iter(future_set)) if future_set and len(future_set) == 1 else None
                    if future == FACTOR_HORIZONS[0]:
                        baseline_present += baseline is not None
                        baseline_nonzero += baseline not in (None, 0)
                    future_present += projected is not None
                    if baseline not in (None, 0) and projected is not None:
                        factor = projected / baseline
                        factors.append(factor)
                        unchanged += math.isclose(factor, 1.0, rel_tol=0, abs_tol=1e-12)
                future_results[future] = {
                    "future_present": future_present,
                    "factor_summary": summarize(factors),
                    "factor_direction_counts": factor_directions(factors),
                    "unchanged_factor_count": unchanged,
                }
            total_coverage[metric][scenario] = {
                "baseline_present": baseline_present,
                "baseline_nonzero": baseline_nonzero,
                "future": future_results,
            }

    reconciliation_groups = 0
    reconciliation_matches = 0
    max_reconciliation_difference = 0.0
    contributor_counts: dict[str, dict[str, Counter[str]]] = defaultdict(
        lambda: defaultdict(Counter)
    )
    contributor_combinations: dict[str, dict[str, Counter[tuple[str, ...]]]] = defaultdict(
        lambda: defaultdict(Counter)
    )
    for report in reports:
        for scenario in SCENARIOS:
            for horizon in ("2025", "2050", "2100"):
                total_set = report["totals"].get((scenario, horizon, "adjustedTotalDamage"))
                if not total_set or len(total_set) != 1:
                    continue
                total = next(iter(total_set))
                contributors: list[str] = []
                hazard_sum = 0.0
                for hazard in hazards:
                    values = report["hazard_damage"].get(
                        (scenario, horizon, hazard, "adjustedHazardDamage")
                    )
                    if values and len(values) == 1:
                        contributors.append(hazard)
                        hazard_sum += next(iter(values))
                difference = total - hazard_sum
                reconciliation_groups += 1
                max_reconciliation_difference = max(
                    max_reconciliation_difference, abs(difference)
                )
                reconciliation_matches += math.isclose(
                    total, hazard_sum, rel_tol=0, abs_tol=1e-12
                )
                contributor_counts[scenario][horizon].update(contributors)
                contributor_combinations[scenario][horizon][tuple(sorted(contributors))] += 1

    coordinate_result: dict[str, object]
    if grid:
        matches = 0
        coordinate_matches = 0
        state_matches = 0
        iso_matches = 0
        for report in reports:
            row = grid.get(report["cell_id"])
            if row is None:
                continue
            matches += 1
            lat, lon = report["coordinates"]
            coordinate_matches += math.isclose(lat, float(row["lat_center"])) and math.isclose(
                lon, float(row["lon_center"])
            )
            parts = report["asset_name"].split("_")
            state_matches += len(parts) > 2 and parts[2] == row["state_abbr"]
            expected_iso = row["iso_rto"]
            asset_name = report["asset_name"]
            iso_matches += expected_iso in asset_name or (
                expected_iso.startswith("Non-ISO") and "Non-ISO" in asset_name
            )
        coordinate_result = {
            "grid_row_count": len(grid),
            "matched_cell_ids": matches,
            "coordinate_matches": coordinate_matches,
            "state_matches": state_matches,
            "iso_name_matches": iso_matches,
        }
    else:
        coordinate_result = {"not_checked": True}

    raw_adjusted_mismatches = Counter()
    raw_adjusted_comparable = Counter()
    for report in reports:
        for row in report["rows"]:
            for raw_name, adjusted_name in RAW_ADJUSTED_PAIRS:
                raw_value = number(row.get(raw_name))
                adjusted_value = number(row.get(adjusted_name))
                if raw_value is not None and adjusted_value is not None:
                    raw_adjusted_comparable[f"{raw_name}|{adjusted_name}"] += 1
                    if not math.isclose(raw_value, adjusted_value, rel_tol=0, abs_tol=1e-12):
                        raw_adjusted_mismatches[f"{raw_name}|{adjusted_name}"] += 1

    output = {
        "dataset": {
            "source_zip": str(args.zip_path),
            "csv_files": len(reports),
            "xlsx_files": sum(".xlsx" in suffixes for suffixes in archive_stems.values()),
            "paired_csv_xlsx_stems": sum(
                suffixes == {".csv", ".xlsx"} for suffixes in archive_stems.values()
            ),
            "unique_cell_ids": len({report["cell_id"] for report in reports}),
            "duplicate_cell_ids": len(reports) - len({report["cell_id"] for report in reports}),
            "row_counts": dict(Counter(report["row_count"] for report in reports)),
            "column_counts": dict(Counter(len(report["columns"]) for report in reports)),
            "schema_variants": len({tuple(report["columns"]) for report in reports}),
            "report_dates": sorted({report["report_date"] for report in reports}),
            "ticcs_subclasses": sorted({report["ticcs_subclass"] for report in reports}),
            "ticcs_subclass_names": sorted(
                {report["ticcs_subclass_name"] for report in reports}
            ),
            "asset_types": sorted(
                {
                    report["workbook_inputs"].get("asset_type")
                    for report in reports
                    if report["workbook_inputs"].get("asset_type")
                }
            ),
            "asset_values": sorted(
                {
                    report["workbook_inputs"].get("asset_value")
                    for report in reports
                    if report["workbook_inputs"].get("asset_value") is not None
                }
            ),
            "asset_revenues": sorted(
                {
                    report["workbook_inputs"].get("asset_revenue")
                    for report in reports
                    if report["workbook_inputs"].get("asset_revenue") is not None
                }
            ),
            "scenarios": sorted(
                {row["scenario"] for report in reports for row in report["rows"]}
            ),
            "time_horizons": sorted(
                {row["timeHorizon"] for report in reports for row in report["rows"]},
                key=lambda value: (-1 if value == "Historical" else int(value)),
            ),
            "hazards": hazards,
            "inconsistent_total_groups": sum(
                len(report["inconsistent_totals"]) for report in reports
            ),
            "inconsistent_hazard_groups": sum(
                len(report["inconsistent_hazards"]) for report in reports
            ),
        },
        "grid_center_verification": coordinate_result,
        "hazard_coverage": hazard_coverage,
        "hazard_factor_summaries": hazard_factor_summaries,
        "total_metric_coverage_and_factors": total_coverage,
        "total_damage_reconciliation": {
            "groups_checked": reconciliation_groups,
            "groups_matching": reconciliation_matches,
            "tolerance": 1e-12,
            "max_absolute_difference": max_reconciliation_difference,
        },
        "damage_contributors": {
            scenario: {
                horizon: {
                    "hazard_file_counts": dict(contributor_counts[scenario][horizon]),
                    "combination_file_counts": {
                        " + ".join(combo): count
                        for combo, count in contributor_combinations[scenario][horizon].items()
                    },
                }
                for horizon in ("2025", "2050", "2100")
            }
            for scenario in SCENARIOS
        },
        "raw_adjusted_comparison": {
            "comparable_row_counts": dict(raw_adjusted_comparable),
            "mismatch_counts": dict(raw_adjusted_mismatches),
        },
    }

    # Remove the raw rows and non-serializable working dictionaries before output.
    args.output_path.parent.mkdir(parents=True, exist_ok=True)
    args.output_path.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {args.output_path}")

    if args.manifest_path:
        args.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        fieldnames = [
            "cell_id",
            "lat_center",
            "lon_center",
            "state_abbr",
            "iso_rto",
            "gas_asset_id",
            "gas_asset_name",
            "gas_ticcs_subclass",
            "gas_ticcs_subclass_name",
        ]
        with args.manifest_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
            writer.writeheader()
            for report in sorted(reports, key=lambda item: int(item["cell_id"])):
                grid_row = grid.get(report["cell_id"], {})
                writer.writerow(
                    {
                        "cell_id": report["cell_id"],
                        "lat_center": report["coordinates"][0],
                        "lon_center": report["coordinates"][1],
                        "state_abbr": grid_row.get("state_abbr", ""),
                        "iso_rto": grid_row.get("iso_rto", ""),
                        "gas_asset_id": report["asset_id"],
                        "gas_asset_name": report["asset_name"],
                        "gas_ticcs_subclass": report["ticcs_subclass"],
                        "gas_ticcs_subclass_name": report["ticcs_subclass_name"],
                    }
                )
        print(f"Wrote {args.manifest_path}")


if __name__ == "__main__":
    main()

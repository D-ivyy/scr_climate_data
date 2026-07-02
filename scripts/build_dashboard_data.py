#!/usr/bin/env python3
"""Build static-dashboard JSON from SCR returned output workbooks."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zipfile import ZipFile


MAIN_NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
RELS_NS = {"r": "http://schemas.openxmlformats.org/package/2006/relationships"}
OFFICE_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
CELL_REF_RE = re.compile(r"([A-Z]+)([0-9]+)")
RATING_ORDER = {letter: index for index, letter in enumerate("ABCDEFG", start=1)}

PHYSICAL_REQUIRED_COLUMNS = {
    "assetId",
    "assetName",
    "geolocationCoordinates",
    "countryCode",
    "climateZone",
    "ticcsSubClass",
    "ticcsSubClassName",
    "scenario",
    "timeHorizon",
    "indicator",
    "indicatorValue",
    "indicatorUnit",
    "indicatorRating",
    "hazard",
    "HazardRating",
    "adjustedHazardValueImpact",
    "hazardExposureRating",
    "adjustedHazardExposureRating",
    "adjustedTotalValueImpact",
    "physicalExposureRating",
    "adjustedPhysicalExposureRating",
}

TRANSITION_REQUIRED_COLUMNS = {
    "assetId",
    "assetName",
    "geolocationCoordinates",
    "countryCode",
    "climateZone",
    "ticcsSubClass",
    "ticcsSubClassName",
    "scenario",
    "timeHorizon",
    "indicator",
    "indicatorValue",
    "indicatorUnit",
    "subrisk",
    "adjustedSubriskRevenueImpact",
    "subriskExposureRating",
    "adjustedSubriskExposureRating",
    "transitionExposureRating",
    "adjustedTransitionExposureRating",
}

MANIFEST_FIELDS_TO_COPY = [
    "scr_run_id",
    "scr_grain",
    "plant_uuid",
    "generator_uuid",
    "plant_slug",
    "eia_plant_id",
    "eia_generator_code",
    "workspace_id",
    "workspace_slug",
    "portfolio_id",
    "portfolio_name",
    "portfolio_asset_id",
    "source_type",
    "plant_name",
    "asset_type",
    "address",
    "latitude",
    "longitude",
    "revenues",
    "asset_value",
    "valuation_year",
]


class WorkbookError(ValueError):
    """Raised when an SCR workbook cannot be parsed as expected."""


def column_index(column_name: str) -> int:
    value = 0
    for char in column_name:
        value = value * 26 + (ord(char) - 64)
    return value - 1


def normalize_target(target: str) -> str:
    target = target.lstrip("/")
    if not target.startswith("xl/"):
        target = f"xl/{target}"
    return target


def load_shared_strings(zip_file: ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in zip_file.namelist():
        return []
    root = ET.fromstring(zip_file.read("xl/sharedStrings.xml"))
    strings: list[str] = []
    for item in root.findall("m:si", MAIN_NS):
        strings.append("".join(text.text or "" for text in item.findall(".//m:t", MAIN_NS)))
    return strings


def cell_value(cell: ET.Element, shared_strings: list[str]) -> Any:
    cell_type = cell.get("t")
    if cell_type == "inlineStr":
        inline = cell.find("m:is", MAIN_NS)
        if inline is None:
            return ""
        return "".join(text.text or "" for text in inline.findall(".//m:t", MAIN_NS))

    value = cell.find("m:v", MAIN_NS)
    if value is None or value.text is None:
        return None

    raw = value.text
    if cell_type == "s":
        try:
            return shared_strings[int(raw)]
        except (IndexError, ValueError):
            return raw
    if cell_type == "b":
        return raw == "1"

    try:
        if "." in raw or "e" in raw.lower():
            return float(raw)
        return int(raw)
    except ValueError:
        return raw


def output_sheet_path(zip_file: ZipFile, workbook_path: Path) -> str:
    workbook = ET.fromstring(zip_file.read("xl/workbook.xml"))
    rels = ET.fromstring(zip_file.read("xl/_rels/workbook.xml.rels"))
    rel_by_id = {
        rel.attrib["Id"]: normalize_target(rel.attrib["Target"])
        for rel in rels.findall("r:Relationship", RELS_NS)
    }

    for sheet in workbook.findall("m:sheets/m:sheet", MAIN_NS):
        if sheet.attrib.get("name") != "Output":
            continue
        rel_id = sheet.attrib.get(f"{{{OFFICE_REL}}}id")
        if not rel_id or rel_id not in rel_by_id:
            raise WorkbookError(f"{workbook_path}: Output sheet relationship is missing.")
        return rel_by_id[rel_id]

    raise WorkbookError(f"{workbook_path}: missing required Output sheet.")


def read_output_rows(workbook_path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    with ZipFile(workbook_path) as zip_file:
        shared_strings = load_shared_strings(zip_file)
        sheet_path = output_sheet_path(zip_file, workbook_path)
        sheet = ET.fromstring(zip_file.read(sheet_path))

    header: list[str] | None = None
    rows: list[dict[str, Any]] = []
    for row in sheet.findall("m:sheetData/m:row", MAIN_NS):
        values_by_index: dict[int, Any] = {}
        max_index = -1
        for cell in row.findall("m:c", MAIN_NS):
            ref = cell.get("r", "")
            match = CELL_REF_RE.match(ref)
            if not match:
                continue
            index = column_index(match.group(1))
            values_by_index[index] = cell_value(cell, shared_strings)
            max_index = max(max_index, index)

        values = [values_by_index.get(index) for index in range(max_index + 1)]
        if header is None:
            header = [str(value) if value is not None else "" for value in values]
            continue

        record = {header[index]: values[index] if index < len(values) else None for index in range(len(header))}
        if any(value not in (None, "") for value in record.values()):
            rows.append(record)

    if header is None:
        raise WorkbookError(f"{workbook_path}: Output sheet is empty.")
    return rows, header


def validate_columns(label: str, columns: list[str], required: set[str]) -> list[str]:
    missing = sorted(required.difference(columns))
    if missing:
        print(f"{label}: missing required columns: {', '.join(missing)}", file=sys.stderr)
    return missing


def to_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def to_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def rating_score(value: Any) -> int:
    return RATING_ORDER.get(str(value or "").strip().upper(), 0)


def best_rating(*values: Any) -> str | None:
    ratings = [str(value).strip().upper() for value in values if str(value or "").strip().upper() in RATING_ORDER]
    if not ratings:
        return None
    return max(ratings, key=rating_score)


def value_for_sort(value: float | None) -> float:
    return value if value is not None else float("-inf")


def asset_record(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "asset_name": row.get("assetName"),
        "scr_asset_id": row.get("assetId"),
        "coordinates": row.get("geolocationCoordinates"),
        "country_code": row.get("countryCode"),
        "climate_zone": row.get("climateZone"),
        "ticcs_sub_class": row.get("ticcsSubClass"),
        "ticcs_sub_class_name": row.get("ticcsSubClassName"),
    }


def read_manifest(path: Path | None) -> dict[str, dict[str, Any]]:
    if path is None:
        return {}
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    manifest: dict[str, dict[str, Any]] = {}
    for row in rows:
        asset_name = row.get("scr_asset_name")
        if not asset_name:
            continue
        manifest[asset_name] = {
            field: row.get(field)
            for field in MANIFEST_FIELDS_TO_COPY
            if field in row and row.get(field) not in (None, "")
        }
    return manifest


def build_assets(physical_rows: list[dict[str, Any]], transition_rows: list[dict[str, Any]], manifest: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    by_asset: dict[str, dict[str, Any]] = {}
    for row in [*physical_rows, *transition_rows]:
        asset_name = row.get("assetName")
        if not asset_name:
            continue
        by_asset.setdefault(str(asset_name), asset_record(row))

    for asset_name, record in by_asset.items():
        if asset_name in manifest:
            record["manifest"] = manifest[asset_name]

    return sorted(by_asset.values(), key=lambda item: str(item.get("asset_name") or ""))


def build_physical(physical_rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    trends_by_key: dict[tuple[str, str, int], dict[str, Any]] = {}
    hazards_by_key: dict[tuple[str, str, int, str], dict[str, Any]] = {}
    indicators: list[dict[str, Any]] = []

    for row in physical_rows:
        asset_name = str(row.get("assetName") or "")
        scenario = str(row.get("scenario") or "")
        horizon = to_int(row.get("timeHorizon"))
        if not asset_name or not scenario or horizon is None:
            continue

        trend_key = (asset_name, scenario, horizon)
        trend = trends_by_key.setdefault(
            trend_key,
            {
                "asset_name": asset_name,
                "scenario": scenario,
                "horizon": horizon,
                "adjusted_total_value_impact": None,
                "adjusted_physical_exposure_rating": None,
            },
        )
        value_impact = to_float(row.get("adjustedTotalValueImpact"))
        if value_impact is not None:
            trend["adjusted_total_value_impact"] = value_impact
        rating = row.get("adjustedPhysicalExposureRating") or row.get("physicalExposureRating")
        if rating:
            trend["adjusted_physical_exposure_rating"] = best_rating(
                trend.get("adjusted_physical_exposure_rating"), rating
            )

        indicator = {
            "asset_name": asset_name,
            "scenario": scenario,
            "horizon": horizon,
            "hazard": row.get("hazard"),
            "indicator": row.get("indicator"),
            "value": to_float(row.get("indicatorValue")),
            "unit": row.get("indicatorUnit") or None,
            "rating": row.get("indicatorRating") or None,
        }
        indicators.append(indicator)

        hazard_name = row.get("hazard")
        if not hazard_name:
            continue
        hazard_key = (asset_name, scenario, horizon, str(hazard_name))
        hazard = hazards_by_key.setdefault(
            hazard_key,
            {
                "asset_name": asset_name,
                "scenario": scenario,
                "horizon": horizon,
                "hazard": hazard_name,
                "adjusted_hazard_value_impact": None,
                "hazard_rating": None,
                "_indicators": [],
                "_rating_counts": Counter(),
            },
        )
        hazard_value = to_float(row.get("adjustedHazardValueImpact"))
        if hazard_value is not None and hazard_value > value_for_sort(hazard["adjusted_hazard_value_impact"]):
            hazard["adjusted_hazard_value_impact"] = hazard_value
        hazard["hazard_rating"] = best_rating(
            hazard.get("hazard_rating"),
            row.get("adjustedHazardExposureRating"),
            row.get("hazardExposureRating"),
            row.get("HazardRating"),
        )
        if indicator["rating"]:
            hazard["_rating_counts"][indicator["rating"]] += 1
        hazard["_indicators"].append(
            {
                "indicator": indicator["indicator"],
                "value": indicator["value"],
                "unit": indicator["unit"],
                "rating": indicator["rating"],
            }
        )

    hazards: list[dict[str, Any]] = []
    for hazard in hazards_by_key.values():
        worst = sorted(
            hazard.pop("_indicators"),
            key=lambda item: (rating_score(item.get("rating")), value_for_sort(item.get("value"))),
            reverse=True,
        )[:3]
        rating_counts = hazard.pop("_rating_counts")
        hazard["worst_indicators"] = worst
        hazard["indicator_rating_counts"] = {letter: rating_counts.get(letter, 0) for letter in "ABCDEFG"}
        hazards.append(hazard)

    return {
        "trends": sorted(trends_by_key.values(), key=lambda item: (item["asset_name"], item["scenario"], item["horizon"])),
        "hazards": sorted(hazards, key=lambda item: (item["asset_name"], item["scenario"], item["horizon"], item["hazard"])),
        "indicators": sorted(
            indicators,
            key=lambda item: (
                item["asset_name"],
                item["scenario"],
                item["horizon"],
                str(item.get("hazard") or ""),
                str(item.get("indicator") or ""),
            ),
        ),
    }


def build_transition(transition_rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    trends_by_key: dict[tuple[str, str, int], dict[str, Any]] = {}
    subrisks: list[dict[str, Any]] = []
    scenario_subrisk_peak: dict[tuple[str, str, str], dict[str, Any]] = {}

    for row in transition_rows:
        asset_name = str(row.get("assetName") or "")
        scenario = str(row.get("scenario") or "")
        horizon = to_int(row.get("timeHorizon"))
        subrisk_name = row.get("subrisk")
        impact = to_float(row.get("adjustedSubriskRevenueImpact"))
        if not asset_name or not scenario or horizon is None:
            continue

        trend_key = (asset_name, scenario, horizon)
        trend = trends_by_key.setdefault(
            trend_key,
            {
                "asset_name": asset_name,
                "scenario": scenario,
                "horizon": horizon,
                "max_adjusted_subrisk_revenue_impact": None,
                "top_subrisk": None,
                "transition_rating": None,
            },
        )
        if impact is not None and impact > value_for_sort(trend["max_adjusted_subrisk_revenue_impact"]):
            trend["max_adjusted_subrisk_revenue_impact"] = impact
            trend["top_subrisk"] = subrisk_name
        transition_rating = row.get("adjustedTransitionExposureRating") or row.get("transitionExposureRating")
        if transition_rating:
            trend["transition_rating"] = best_rating(trend.get("transition_rating"), transition_rating)

        subrisk = {
            "asset_name": asset_name,
            "scenario": scenario,
            "horizon": horizon,
            "indicator": row.get("indicator"),
            "indicator_value": to_float(row.get("indicatorValue")),
            "indicator_unit": row.get("indicatorUnit") or None,
            "subrisk": subrisk_name,
            "adjusted_revenue_impact": impact,
            "rating": row.get("adjustedSubriskExposureRating") or row.get("subriskExposureRating") or None,
        }
        subrisks.append(subrisk)

        if subrisk_name and impact is not None:
            peak_key = (asset_name, scenario, str(subrisk_name))
            peak = scenario_subrisk_peak.get(peak_key)
            if peak is None or impact > peak["value"]:
                scenario_subrisk_peak[peak_key] = {
                    "asset_name": asset_name,
                    "subrisk": subrisk_name,
                    "value": impact,
                    "year": horizon,
                    "rating": subrisk["rating"],
                }

    asset_scenarios = sorted(
        {
            (str(row.get("assetName")), str(row.get("scenario")))
            for row in transition_rows
            if row.get("assetName") and row.get("scenario")
        }
    )
    scenario_rankings: list[dict[str, Any]] = []
    for asset_name, scenario in asset_scenarios:
        peaks = [
            value
            for (peak_asset, peak_scenario, _), value in scenario_subrisk_peak.items()
            if peak_asset == asset_name and peak_scenario == scenario
        ]
        if not peaks:
            continue
        peak = max(peaks, key=lambda item: item["value"])
        direct = scenario_subrisk_peak.get((asset_name, scenario, "Direct_carbon_cost"))
        market = scenario_subrisk_peak.get((asset_name, scenario, "Market_demand_shifts"))
        scenario_rankings.append(
            {
                "asset_name": asset_name,
                "scenario": scenario,
                "peak_impact": peak["value"],
                "peak_year": peak["year"],
                "peak_subrisk": peak["subrisk"],
                "direct_carbon_peak": direct,
                "market_demand_peak": market,
            }
        )

    return {
        "scenario_rankings": sorted(
            scenario_rankings,
            key=lambda item: (item["asset_name"], -item["peak_impact"]),
        ),
        "trends": sorted(trends_by_key.values(), key=lambda item: (item["asset_name"], item["scenario"], item["horizon"])),
        "subrisks": sorted(
            subrisks,
            key=lambda item: (
                item["asset_name"],
                item["scenario"],
                item["horizon"],
                str(item.get("subrisk") or ""),
                str(item.get("indicator") or ""),
            ),
        ),
    }


def build_dashboard_data(args: argparse.Namespace) -> dict[str, Any]:
    physical_rows, physical_columns = read_output_rows(args.physical)
    transition_rows, transition_columns = read_output_rows(args.transition)

    missing = {
        "physical": validate_columns("physical", physical_columns, PHYSICAL_REQUIRED_COLUMNS),
        "transition": validate_columns("transition", transition_columns, TRANSITION_REQUIRED_COLUMNS),
    }
    if missing["physical"] or missing["transition"]:
        raise SystemExit("Cannot build dashboard data because required SCR columns are missing.")

    manifest = read_manifest(args.manifest)
    data = {
        "meta": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "physical_source": str(args.physical),
            "transition_source": str(args.transition),
            "manifest_source": str(args.manifest) if args.manifest else None,
            "physical_rows": len(physical_rows),
            "transition_rows": len(transition_rows),
            "missing_fields": missing,
        },
        "assets": build_assets(physical_rows, transition_rows, manifest),
        "physical": build_physical(physical_rows),
        "transition": build_transition(transition_rows),
    }
    return data


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--physical", type=Path, required=True, help="SCR returned physical-risks workbook.")
    parser.add_argument("--transition", type=Path, required=True, help="SCR returned transition-risks workbook.")
    parser.add_argument("--manifest", type=Path, help="Optional private SCR manifest CSV for join-back fields.")
    parser.add_argument("--out", type=Path, required=True, help="Output JSON path for the static dashboard.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    data = build_dashboard_data(args)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote {args.out}")
    print(f"Physical rows: {data['meta']['physical_rows']}")
    print(f"Transition rows: {data['meta']['transition_rows']}")
    print(f"Assets: {len(data['assets'])}")


if __name__ == "__main__":
    main()

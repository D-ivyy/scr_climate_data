#!/usr/bin/env python3
"""Task-indexed SCR transition-risk extractor for Cloud Run Jobs.

The extractor intentionally preserves SCR numeric impacts without scaling or
financial interpretation. It converts each 216-row workbook into 54 compact
scenario/horizon records while retaining raw and adjusted source fields.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import tempfile
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PACKAGE_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
CELL_ID_RE = re.compile(r"Cell_(\d+)_")
CELL_REF_RE = re.compile(r"([A-Z]+)")
REQUIRED_HEADERS = (
    "assetId",
    "assetName",
    "reportDate",
    "geolocationCoordinates",
    "countryCode",
    "climateZone",
    "ticcsSubClass",
    "ticcsSubClassName",
    "scenario",
    "timeHorizon",
    "indicator",
    "indicatorUnit",
    "indicatorValue",
    "subrisk",
    "subriskRevenueImpact",
    "adjustedSubriskRevenueImpact",
    "subriskExposureRating",
    "adjustedSubriskExposureRating",
    "transitionExposureRating",
    "adjustedTransitionExposureRating",
)
EXPECTED_INDICATORS = (
    "Carbon price",
    "Revenue growth",
    "Scope 1&2 emissions intensity",
    "Scope 3 emissions intensity",
)
EXPECTED_SUBRISKS = ("Direct Carbon Cost", "Market Demand Shifts")
ECONOMIC_FINGERPRINT_COLUMNS = (
    "scenario",
    "timeHorizon",
    "indicator",
    "indicatorUnit",
    "indicatorValue",
    "subrisk",
    "subriskRevenueImpact",
    "adjustedSubriskRevenueImpact",
    "subriskExposureRating",
    "adjustedSubriskExposureRating",
    "transitionExposureRating",
    "adjustedTransitionExposureRating",
)


def run(*args: str) -> None:
    subprocess.run(args, check=True)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_json(value) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def column_index(cell_ref: str) -> int:
    letters = CELL_REF_RE.match(cell_ref).group(1)
    value = 0
    for letter in letters:
        value = value * 26 + ord(letter) - ord("A") + 1
    return value - 1


def shared_strings(archive: zipfile.ZipFile) -> list[str]:
    try:
        root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
    except KeyError:
        return []
    return [
        "".join(node.text or "" for node in item.iter(f"{{{MAIN_NS}}}t"))
        for item in root.findall(f"{{{MAIN_NS}}}si")
    ]


def output_sheet_path(archive: zipfile.ZipFile) -> str:
    workbook = ET.fromstring(archive.read("xl/workbook.xml"))
    relationship_id = None
    for sheet in workbook.findall(f".//{{{MAIN_NS}}}sheet"):
        if sheet.attrib.get("name") == "Output":
            relationship_id = sheet.attrib.get(f"{{{REL_NS}}}id")
            break
    if not relationship_id:
        raise ValueError("Missing Output worksheet")
    relationships = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    for relation in relationships.findall(f"{{{PACKAGE_REL_NS}}}Relationship"):
        if relation.attrib.get("Id") == relationship_id:
            target = relation.attrib["Target"].lstrip("/")
            return target if target.startswith("xl/") else f"xl/{target}"
    raise ValueError("Output worksheet relationship is missing")


def cell_value(cell: ET.Element, strings: list[str]):
    value_type = cell.attrib.get("t")
    if value_type == "inlineStr":
        text = "".join(node.text or "" for node in cell.iter(f"{{{MAIN_NS}}}t"))
        return text if text != "" else None
    value_node = cell.find(f"{{{MAIN_NS}}}v")
    if value_node is None or value_node.text is None:
        return None
    text = value_node.text
    if value_type == "s":
        return strings[int(text)]
    if value_type in {"str", "e"}:
        return text
    if value_type == "b":
        return text == "1"
    number = float(text)
    return int(number) if number.is_integer() else number


def read_output(path: Path) -> tuple[list[str], list[dict]]:
    with zipfile.ZipFile(path) as archive:
        strings = shared_strings(archive)
        sheet = ET.fromstring(archive.read(output_sheet_path(archive)))
    xml_rows = sheet.findall(f".//{{{MAIN_NS}}}sheetData/{{{MAIN_NS}}}row")
    if not xml_rows:
        raise ValueError("Output worksheet is empty")

    def values(xml_row: ET.Element) -> dict[int, object]:
        return {
            column_index(cell.attrib["r"]): cell_value(cell, strings)
            for cell in xml_row.findall(f"{{{MAIN_NS}}}c")
        }

    header_values = values(xml_rows[0])
    headers = [header_values.get(index) for index in range(max(header_values) + 1)]
    if tuple(headers) != REQUIRED_HEADERS:
        missing = [header for header in REQUIRED_HEADERS if header not in headers]
        extra = [header for header in headers if header not in REQUIRED_HEADERS]
        raise ValueError(f"Unexpected Output schema; missing={missing}, extra={extra}")
    output = []
    for xml_row in xml_rows[1:]:
        row_values = values(xml_row)
        output.append({header: row_values.get(index) for index, header in enumerate(headers)})
    return headers, output


def distinct(rows: list[dict], field: str, *, allow_blank: bool = True):
    values = []
    for row in rows:
        value = row[field]
        if value in (None, ""):
            continue
        if value not in values:
            values.append(value)
    if len(values) > 1:
        raise ValueError(f"Expected one repeated {field}; found {values}")
    if not values:
        if allow_blank:
            return None
        raise ValueError(f"Required field {field} is blank")
    return values[0]


def excel_date(value):
    if isinstance(value, (int, float)):
        return (dt.datetime(1899, 12, 30) + dt.timedelta(days=value)).date().isoformat()
    return value


def compact_rows(rows: list[dict]) -> list[dict]:
    grouped: dict[tuple[str, int], list[dict]] = {}
    for row in rows:
        key = (str(row["scenario"]), int(row["timeHorizon"]))
        grouped.setdefault(key, []).append(row)
    output = []
    for (scenario, horizon), group in sorted(grouped.items()):
        if len(group) != 4:
            raise ValueError(f"Expected four indicator rows for {scenario}/{horizon}; found {len(group)}")
        indicator_rows = {row["indicator"]: row for row in group}
        if set(indicator_rows) != set(EXPECTED_INDICATORS):
            raise ValueError(f"Unexpected indicators for {scenario}/{horizon}: {sorted(indicator_rows)}")
        subrisks = {}
        for subrisk in EXPECTED_SUBRISKS:
            subrisk_group = [row for row in group if row["subrisk"] == subrisk]
            if not subrisk_group:
                raise ValueError(f"Missing {subrisk} for {scenario}/{horizon}")
            subrisks[subrisk] = {
                "subriskRevenueImpact": distinct(subrisk_group, "subriskRevenueImpact"),
                "adjustedSubriskRevenueImpact": distinct(
                    subrisk_group, "adjustedSubriskRevenueImpact"
                ),
                "subriskExposureRating": distinct(
                    subrisk_group, "subriskExposureRating", allow_blank=False
                ),
                "adjustedSubriskExposureRating": distinct(
                    subrisk_group, "adjustedSubriskExposureRating", allow_blank=False
                ),
            }
        output.append(
            {
                "scenario": scenario,
                "timeHorizon": horizon,
                "indicators": {
                    indicator: {
                        "indicatorUnit": indicator_rows[indicator]["indicatorUnit"],
                        "indicatorValue": indicator_rows[indicator]["indicatorValue"],
                    }
                    for indicator in EXPECTED_INDICATORS
                },
                "subrisks": subrisks,
                "transitionExposureRating": distinct(
                    group, "transitionExposureRating", allow_blank=False
                ),
                "adjustedTransitionExposureRating": distinct(
                    group, "adjustedTransitionExposureRating", allow_blank=False
                ),
            }
        )
    return output


def extract_workbook(path: Path, source_uri: str | None = None) -> dict:
    match = CELL_ID_RE.search(path.name)
    cell_id = int(match.group(1)) if match else None
    try:
        headers, rows = read_output(path)
        if len(rows) != 216:
            raise ValueError(f"Expected 216 Output rows; found {len(rows)}")
        compact = compact_rows(rows)
        if len(compact) != 54:
            raise ValueError(f"Expected 54 compact rows; found {len(compact)}")
        metadata_fields = (
            "assetId",
            "assetName",
            "reportDate",
            "geolocationCoordinates",
            "countryCode",
            "climateZone",
            "ticcsSubClass",
            "ticcsSubClassName",
        )
        metadata = {
            field: distinct(rows, field, allow_blank=False) for field in metadata_fields
        }
        metadata["reportDate"] = excel_date(metadata["reportDate"])
        fingerprint_rows = [
            [row[column] for column in ECONOMIC_FINGERPRINT_COLUMNS]
            for row in sorted(
                rows,
                key=lambda row: (
                    str(row["scenario"]),
                    int(row["timeHorizon"]),
                    str(row["subrisk"]),
                    str(row["indicator"]),
                ),
            )
        ]
        return {
            "filename": path.name,
            "sourceUri": source_uri,
            "cellId": cell_id,
            "status": "ok",
            "rowCount": len(rows),
            "compactRowCount": len(compact),
            "headers": headers,
            "schemaSha256": sha256_json(headers),
            "economicContentFingerprint": sha256_json(fingerprint_rows),
            "metadata": metadata,
            "compactRows": compact,
        }
    except Exception as error:  # isolate workbook errors for task diagnostics
        return {
            "filename": path.name,
            "sourceUri": source_uri,
            "cellId": cell_id,
            "status": "error",
            "error": f"{type(error).__name__}: {error}",
        }


def local_mode(args: argparse.Namespace) -> int:
    results = [extract_workbook(path) for path in sorted(args.local_input_dir.glob("*.xlsx"))]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({"files": results}, indent=2) + "\n", encoding="utf-8")
    errors = sum(result["status"] != "ok" for result in results)
    print(json.dumps({"files": len(results), "errors": errors}))
    return 1 if errors else 0


def cloud_mode() -> int:
    task_index = int(os.environ["CLOUD_RUN_TASK_INDEX"])
    task_count = int(os.environ["CLOUD_RUN_TASK_COUNT"])
    inventory_uri = os.environ["SCR_INVENTORY_URI"]
    inventory_sha = os.environ["SCR_INVENTORY_SHA256"]
    output_root = os.environ["SCR_OUTPUT_ROOT"].rstrip("/")
    with tempfile.TemporaryDirectory(prefix="scr_transition_task_") as temporary:
        root = Path(temporary)
        inventory_path = root / "source_inventory.json"
        run("gcloud", "--quiet", "storage", "cp", inventory_uri, str(inventory_path))
        if sha256_file(inventory_path) != inventory_sha:
            raise ValueError("Source inventory SHA-256 mismatch")
        inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
        all_uris = sorted(inventory["uris"])
        uris = [uri for index, uri in enumerate(all_uris) if index % task_count == task_index]
        workbook_dir = root / "workbooks"
        workbook_dir.mkdir()
        if uris:
            run("gcloud", "--quiet", "storage", "cp", *uris, f"{workbook_dir}/")
        uri_by_name = {Path(uri).name: uri for uri in uris}
        results = [
            extract_workbook(path, uri_by_name[path.name])
            for path in sorted(workbook_dir.glob("*.xlsx"))
        ]
        errors = [result for result in results if result["status"] != "ok"]
        payload = {
            "task_index": task_index,
            "task_count": task_count,
            "source_inventory_sha256": inventory_sha,
            "files": results,
        }
        output_path = root / "results.json"
        output_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        output_uri = f"{output_root}/task={task_index:05d}/results.json"
        run(
            "gcloud",
            "--quiet",
            "storage",
            "cp",
            "--if-generation-match=0",
            output_path.as_posix(),
            output_uri,
        )
        print(
            json.dumps(
                {
                    "task": task_index,
                    "files": len(results),
                    "errors": len(errors),
                    "output": output_uri,
                }
            )
        )
        return 1 if errors else 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--local-input-dir", type=Path)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


if __name__ == "__main__":
    arguments = parse_args()
    if arguments.local_input_dir:
        if not arguments.output:
            raise SystemExit("Local mode needs --output")
        raise SystemExit(local_mode(arguments))
    raise SystemExit(cloud_mode())

#!/usr/bin/env python3
"""Task-indexed SCR XLSX extractor for Cloud Run Jobs.

The cloud path uses only Python's standard library plus the Cloud SDK already
present in the runtime image. The fixed OOXML extraction contract is validated
locally against @oai/artifact-tool results before a full execution is launched.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PACKAGE_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
CELL_ID_RE = re.compile(r"Cell_(\d+)_")
CELL_REF_RE = re.compile(r"([A-Z]+)")
REQUIRED_HEADERS = ("scenario", "timeHorizon", "adjustedTotalDamage")


def run(*args: str) -> None:
    subprocess.run(args, check=True)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


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
    values = []
    for item in root.findall(f"{{{MAIN_NS}}}si"):
        values.append("".join(node.text or "" for node in item.iter(f"{{{MAIN_NS}}}t")))
    return values


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
        return "".join(node.text or "" for node in cell.iter(f"{{{MAIN_NS}}}t"))
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


def distinct(values: list):
    present = [value for value in values if value not in (None, "")]
    distinct_values = []
    for value in present:
        if value not in distinct_values:
            distinct_values.append(value)
    if len(distinct_values) > 1:
        raise ValueError(f"Expected one repeated total-damage value; found {len(distinct_values)}")
    return distinct_values[0] if distinct_values else None


def extract_workbook(path: Path) -> dict:
    match = CELL_ID_RE.search(path.name)
    cell_id = int(match.group(1)) if match else None
    try:
        with zipfile.ZipFile(path) as archive:
            strings = shared_strings(archive)
            sheet_path = output_sheet_path(archive)
            sheet = ET.fromstring(archive.read(sheet_path))
        rows = sheet.findall(f".//{{{MAIN_NS}}}sheetData/{{{MAIN_NS}}}row")
        if not rows:
            raise ValueError("Output worksheet is empty")
        header_by_index = {}
        for cell in rows[0].findall(f"{{{MAIN_NS}}}c"):
            header_by_index[column_index(cell.attrib["r"])] = cell_value(cell, strings)
        max_column = max(header_by_index)
        headers = [header_by_index.get(index) for index in range(max_column + 1)]
        indexes = {}
        for header in REQUIRED_HEADERS:
            if header not in headers:
                raise ValueError(f"Missing required column {header}")
            indexes[header] = headers.index(header)
        grouped: dict[str, dict[str, list]] = {}
        for row in rows[1:]:
            selected = {}
            needed_indexes = set(indexes.values())
            for cell in row.findall(f"{{{MAIN_NS}}}c"):
                index = column_index(cell.attrib["r"])
                if index in needed_indexes:
                    selected[index] = cell_value(cell, strings)
            scenario = selected.get(indexes["scenario"])
            horizon_value = selected.get(indexes["timeHorizon"])
            if scenario in (None, "") or horizon_value in (None, ""):
                continue
            horizon = str(horizon_value)
            grouped.setdefault(str(scenario), {}).setdefault(horizon, []).append(
                selected.get(indexes["adjustedTotalDamage"])
            )
        totals = {
            scenario: {horizon: distinct(values) for horizon, values in horizons.items()}
            for scenario, horizons in grouped.items()
        }
        return {
            "filename": path.name,
            "cellId": cell_id,
            "status": "ok",
            "rowCount": len(rows) - 1,
            "headers": headers,
            "totals": totals,
        }
    except Exception as error:  # isolate workbook errors for task diagnostics
        return {
            "filename": path.name,
            "cellId": cell_id,
            "status": "error",
            "error": f"{type(error).__name__}: {error}",
        }


def local_mode(args: argparse.Namespace) -> int:
    reference_files = []
    for reference_path in sorted(args.reference_shards.glob("*.json")):
        reference_files.extend(json.loads(reference_path.read_text())["files"])
    filenames = sorted({item["filename"] for item in reference_files})
    results = [extract_workbook(args.local_input_dir / filename) for filename in filenames]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({"files": results}, indent=2) + "\n")
    print(json.dumps({"files": len(results), "errors": sum(r["status"] != "ok" for r in results)}))
    return 1 if any(result["status"] != "ok" for result in results) else 0


def cloud_mode() -> int:
    task_index = int(os.environ["CLOUD_RUN_TASK_INDEX"])
    task_count = int(os.environ["CLOUD_RUN_TASK_COUNT"])
    inventory_uri = os.environ["SCR_INVENTORY_URI"]
    inventory_sha = os.environ["SCR_INVENTORY_SHA256"]
    output_root = os.environ["SCR_OUTPUT_ROOT"].rstrip("/")
    with tempfile.TemporaryDirectory(prefix="scr_task_") as temporary:
        root = Path(temporary)
        inventory_path = root / "source_inventory.json"
        run("gcloud", "--quiet", "storage", "cp", inventory_uri, str(inventory_path))
        if sha256(inventory_path) != inventory_sha:
            raise ValueError("Source inventory SHA-256 mismatch")
        inventory = json.loads(inventory_path.read_text())
        all_uris = sorted(inventory["uris"])
        uris = [uri for index, uri in enumerate(all_uris) if index % task_count == task_index]
        workbook_dir = root / "workbooks"
        workbook_dir.mkdir()
        if uris:
            run("gcloud", "--quiet", "storage", "cp", *uris, f"{workbook_dir}/")
        results = [extract_workbook(path) for path in sorted(workbook_dir.glob("*.xlsx"))]
        errors = [result for result in results if result["status"] != "ok"]
        payload = {
            "task_index": task_index,
            "task_count": task_count,
            "source_inventory_sha256": inventory_sha,
            "files": results,
        }
        output_path = root / "results.json"
        output_path.write_text(json.dumps(payload, indent=2) + "\n")
        output_uri = f"{output_root}/task={task_index:05d}/results.json"
        run(
            "gcloud", "--quiet", "storage", "cp", "--if-generation-match=0",
            output_path.as_posix(), output_uri,
        )
        print(json.dumps({"task": task_index, "files": len(results), "errors": len(errors), "output": output_uri}))
        return 1 if errors else 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--local-input-dir", type=Path)
    parser.add_argument("--reference-shards", type=Path)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


if __name__ == "__main__":
    arguments = parse_args()
    if arguments.local_input_dir:
        if not arguments.reference_shards or not arguments.output:
            raise SystemExit("Local mode needs --reference-shards and --output")
        raise SystemExit(local_mode(arguments))
    raise SystemExit(cloud_mode())

#!/usr/bin/env python3
"""Stream SCR transition result shards into a full-corpus QA summary."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import subprocess
import tempfile
from collections import Counter, defaultdict
from pathlib import Path


def run_text(args: list[str]) -> str:
    return subprocess.check_output(args, text=True)


def sha256_lines(values: list[str]) -> str:
    payload = "".join(f"{value}\n" for value in values).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def update_distribution(distribution: dict, value) -> None:
    if value is None:
        distribution["null_count"] += 1
        return
    number = float(value)
    distribution["non_null_count"] += 1
    distribution["minimum"] = (
        number if distribution["minimum"] is None else min(distribution["minimum"], number)
    )
    distribution["maximum"] = (
        number if distribution["maximum"] is None else max(distribution["maximum"], number)
    )
    distribution["negative_count"] += number < 0
    distribution["zero_count"] += number == 0
    distribution["abs_above_one_count"] += abs(number) > 1
    distribution["abs_above_100_count"] += abs(number) > 100


def new_distribution() -> dict:
    return {
        "non_null_count": 0,
        "null_count": 0,
        "minimum": None,
        "maximum": None,
        "negative_count": 0,
        "zero_count": 0,
        "abs_above_one_count": 0,
        "abs_above_100_count": 0,
    }


def main() -> None:
    shards_prefix = os.environ["SCR_SHARDS_PREFIX"].rstrip("/") + "/"
    expected_files = int(os.environ["SCR_EXPECTED_FILES"])
    expected_shards = int(os.environ.get("SCR_EXPECTED_SHARDS", "128"))
    summary_uri = os.environ["SCR_SUMMARY_URI"]

    listing = run_text(
        ["gcloud", "storage", "ls", "--recursive", f"{shards_prefix}**"]
    )
    shard_uris = sorted(
        line.strip() for line in listing.splitlines() if line.strip().endswith("results.json")
    )

    task_indices = []
    inventory_hashes = set()
    files_seen = 0
    errors = []
    cell_ids = []
    schema_hashes = Counter()
    fingerprint_rows = defaultdict(list)
    scenarios = set()
    horizons = set()
    indicators = set()
    subrisks = set()
    report_dates = set()
    ticcs_subclasses = set()
    ticcs_names = set()
    compact_row_count = 0
    impact_distributions = {
        "raw": new_distribution(),
        "adjusted": new_distribution(),
    }
    raw_adjusted_equal = 0
    raw_adjusted_comparable = 0
    subrisk_ratings = defaultdict(set)
    overall_ratings = set()

    for shard_uri in shard_uris:
        completed = subprocess.run(
            ["gcloud", "storage", "cat", shard_uri],
            text=True,
            capture_output=True,
        )
        if completed.returncode:
            raise RuntimeError(f"Could not read {shard_uri}: {completed.stderr[-2000:]}")
        payload = json.loads(completed.stdout)
        task_indices.append(int(payload["task_index"]))
        inventory_hashes.add(payload["source_inventory_sha256"])
        for item in payload["files"]:
            files_seen += 1
            if item["status"] != "ok":
                errors.append(
                    {
                        "filename": item["filename"],
                        "cellId": item.get("cellId"),
                        "error": item.get("error"),
                    }
                )
                continue
            cell_id = int(item["cellId"])
            cell_ids.append(cell_id)
            schema_hashes[item["schemaSha256"]] += 1
            metadata = item["metadata"]
            report_dates.add(metadata["reportDate"])
            ticcs_subclasses.add(metadata["ticcsSubClass"])
            ticcs_names.add(metadata["ticcsSubClassName"])
            fingerprint = item["economicContentFingerprint"]
            fingerprint_rows[fingerprint].append(
                {
                    "cell_id": cell_id,
                    "asset_id": metadata["assetId"],
                    "report_date": metadata["reportDate"],
                }
            )
            for compact in item["compactRows"]:
                compact_row_count += 1
                scenarios.add(compact["scenario"])
                horizons.add(int(compact["timeHorizon"]))
                indicators.update(compact["indicators"])
                subrisks.update(compact["subrisks"])
                overall_ratings.add(compact["adjustedTransitionExposureRating"])
                for subrisk, fields in compact["subrisks"].items():
                    raw = fields["subriskRevenueImpact"]
                    adjusted = fields["adjustedSubriskRevenueImpact"]
                    update_distribution(impact_distributions["raw"], raw)
                    update_distribution(impact_distributions["adjusted"], adjusted)
                    if raw is not None and adjusted is not None:
                        raw_adjusted_comparable += 1
                        raw_adjusted_equal += raw == adjusted
                    subrisk_ratings[subrisk].add(fields["adjustedSubriskExposureRating"])

    ordered_cells = sorted(
        (row["cell_id"], fingerprint)
        for fingerprint, rows in fingerprint_rows.items()
        for row in rows
    )
    transitions = [
        {
            "after_cell_id": left[0],
            "before_cell_id": right[0],
            "from_fingerprint": left[1],
            "to_fingerprint": right[1],
        }
        for left, right in zip(ordered_cells, ordered_cells[1:])
        if left[1] != right[1]
    ]
    segments = []
    for cell_id, fingerprint in ordered_cells:
        if not segments or segments[-1]["economic_content_fingerprint"] != fingerprint:
            segments.append(
                {
                    "economic_content_fingerprint": fingerprint,
                    "cell_count": 1,
                    "minimum_cell_id": cell_id,
                    "maximum_cell_id": cell_id,
                }
            )
        else:
            segments[-1]["cell_count"] += 1
            segments[-1]["maximum_cell_id"] = cell_id

    fingerprint_summary = []
    for fingerprint, rows in sorted(
        fingerprint_rows.items(), key=lambda item: (-len(item[1]), item[0])
    ):
        cell_set = sorted(row["cell_id"] for row in rows)
        asset_ids = sorted(row["asset_id"] for row in rows)
        fingerprint_summary.append(
            {
                "economic_content_fingerprint": fingerprint,
                "cell_count": len(rows),
                "minimum_cell_id": cell_set[0],
                "maximum_cell_id": cell_set[-1],
                "minimum_asset_id": asset_ids[0],
                "maximum_asset_id": asset_ids[-1],
                "report_dates": sorted({row["report_date"] for row in rows}),
                "sample_cell_ids": cell_set[:10],
            }
        )

    checks = {
        "expected_shard_count": len(shard_uris) == expected_shards,
        "complete_task_index_set": sorted(task_indices) == list(range(expected_shards)),
        "single_inventory_hash": len(inventory_hashes) == 1,
        "expected_file_count": files_seen == expected_files,
        "zero_parse_errors": not errors,
        "unique_cell_ids": len(cell_ids) == len(set(cell_ids)),
        "expected_compact_rows": compact_row_count == expected_files * 54,
        "single_output_schema": len(schema_hashes) == 1,
        "nine_scenarios": len(scenarios) == 9,
        "six_horizons": len(horizons) == 6,
        "four_indicators": len(indicators) == 4,
        "two_subrisks": len(subrisks) == 2,
    }
    report = {
        "schema_version": "scr_transition_full_corpus_profile_v1",
        "created_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "shards_prefix": shards_prefix,
        "shard_uri_list_sha256": sha256_lines(shard_uris),
        "source_inventory_sha256": sorted(inventory_hashes),
        "expected_files": expected_files,
        "shard_count": len(shard_uris),
        "files_seen": files_seen,
        "successful_files": files_seen - len(errors),
        "parse_error_count": len(errors),
        "parse_errors": errors[:100],
        "unique_cell_count": len(set(cell_ids)),
        "compact_row_count": compact_row_count,
        "schema_hash_counts": dict(schema_hashes),
        "report_dates": sorted(report_dates),
        "ticcs_subclasses": sorted(ticcs_subclasses),
        "ticcs_names": sorted(ticcs_names),
        "scenarios": sorted(scenarios),
        "horizons": sorted(horizons),
        "indicators": sorted(indicators),
        "subrisks": sorted(subrisks),
        "impact_distributions": impact_distributions,
        "raw_adjusted_impact_equal_count": raw_adjusted_equal,
        "raw_adjusted_impact_comparable_count": raw_adjusted_comparable,
        "raw_adjusted_impact_equal_share": (
            raw_adjusted_equal / raw_adjusted_comparable
            if raw_adjusted_comparable
            else None
        ),
        "subrisk_rating_domains": {
            subrisk: sorted(ratings) for subrisk, ratings in sorted(subrisk_ratings.items())
        },
        "overall_rating_domain": sorted(overall_ratings),
        "distinct_economic_content_fingerprints": len(fingerprint_rows),
        "economic_fingerprints": fingerprint_summary,
        "economic_fingerprint_transition_count_in_cell_order": len(transitions),
        "economic_fingerprint_transitions": transitions,
        "economic_fingerprint_contiguous_segments": segments,
        "checks": checks,
    }

    with tempfile.TemporaryDirectory(prefix="scr_transition_summary_") as temporary:
        summary_path = Path(temporary) / "full_corpus_profile.json"
        summary_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        subprocess.run(
            [
                "gcloud",
                "--quiet",
                "storage",
                "cp",
                "--if-generation-match=0",
                str(summary_path),
                summary_uri,
            ],
            check=True,
        )
    print(
        json.dumps(
            {
                "status": "passed" if all(checks.values()) else "failed",
                "files": files_seen,
                "errors": len(errors),
                "fingerprints": len(fingerprint_rows),
                "summary": summary_uri,
            }
        )
    )
    if not all(checks.values()):
        raise SystemExit(1)


if __name__ == "__main__":
    main()

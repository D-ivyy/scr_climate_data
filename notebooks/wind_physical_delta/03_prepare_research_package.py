#!/usr/bin/env python3
"""Finalize immutable Wind filled V1/V2 research-package metadata."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--v1-dir", required=True, type=Path)
    parser.add_argument("--v2-dir", required=True, type=Path)
    parser.add_argument("--validation", required=True, type=Path)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--v1-publication-prefix", required=True)
    parser.add_argument("--v2-publication-prefix", required=True)
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    validation = json.loads(args.validation.read_text(encoding="utf-8"))
    if validation.get("status") != "passed":
        raise ValueError("Nearest-fill validation must pass before package finalization")

    v1_manifest_path = args.v1_dir / "manifest.json"
    v2_manifest_path = args.v2_dir / "manifest.json"
    v1_manifest = json.loads(v1_manifest_path.read_text(encoding="utf-8"))
    v2_manifest = json.loads(v2_manifest_path.read_text(encoding="utf-8"))
    v1_parquet = args.v1_dir / v1_manifest["output_file"]
    v2_parquet = args.v2_dir / v2_manifest["output_file"]
    if sha256(v1_parquet) != v1_manifest["output_sha256"]:
        raise ValueError("V1 Parquet hash does not match manifest")
    if sha256(v2_parquet) != v2_manifest["output_sha256"]:
        raise ValueError("V2 Parquet hash does not match manifest")
    if validation["inputs"]["filled_v1"]["sha256"] != v1_manifest["output_sha256"]:
        raise ValueError("Validation does not describe this V1")
    if validation["inputs"]["filled_v2"]["sha256"] != v2_manifest["output_sha256"]:
        raise ValueError("Validation does not describe this V2")

    qa_path = args.v1_dir / "qa_report.json"
    write_json(qa_path, validation)
    v2_validation_path = args.v2_dir / "nearest_fill_validation.json"
    write_json(v2_validation_path, validation)

    availability = validation["availability"]
    donors = validation["donors"]
    stabilization = validation["stabilization"]
    v1_readme = f"""# SCR Onshore Wind CONUS overall-delta V1 filled research candidate

## Purpose

This candidate converts the completed SCR Onshore Wind extraction into a
canonical 13,085-cell physical-damage factor surface. Raw SCR-derived factors
remain untouched. Cells without a calculable 2025 baseline receive a separate
nearest-metric-eligible Wind donor path for controlled product testing.

```text
factor_raw     = observed SCR ratio; null when no valid baseline exists
factor_filled  = observed ratio or nearest eligible Wind donor ratio
```

## Coverage and provenance

| Item | Value |
|---|---:|
| Rows | {v1_manifest['row_count']:,} |
| Canonical cells | {v1_manifest['canonical_cell_count']:,} |
| Metric-eligible observed cells | {availability['metric_eligible_cells']:,} |
| Nearest-donor-completed cells | {availability['imputed_cells']:,} |
| Raw factor null rows retained | {availability['raw_factor_null_rows']:,} |
| Filled factor null rows | {availability['filled_factor_null_rows']:,} |
| Median donor distance | {donors['distance_km']['median']:.2f} km |
| 95th-percentile donor distance | {donors['distance_km']['p95']:.2f} km |
| Maximum donor distance | {donors['distance_km']['max']:.2f} km |
| Same-state donor share | {donors['same_state_share']:.2%} |

Every imputed row records `is_imputed`, `fill_method`, `source_cell_id`,
`donor_distance_km`, and `quality_status`. Six cells retain 48 late-emerging
raw future-damage values even though their raw factors remain null.

## QA boundary

The QA report verifies key uniqueness, complete filled factors, raw-field parity
with the immutable retain-null V1, complete donor paths, late-emerging raw-value
preservation, and Solar-pattern overlap. This is a research candidate, not yet
the recipient-facing current delivery.

The stabilized V2 candidate compresses {stabilization['filled_compressed_rows']:,}
complete-grid rows and preserves the raw and filled V1 fields.
"""
    v1_readme_path = args.v1_dir / "README.md"
    v1_readme_path.write_text(v1_readme, encoding="utf-8")

    v1_manifest.update(
        {
            "run_id": args.run_id,
            "release_status": "qa_passed_research_candidate",
            "publication_prefix": args.v1_publication_prefix.rstrip("/") + "/",
            "qa_report": qa_path.name,
            "qa_report_sha256": sha256(qa_path),
            "readme": v1_readme_path.name,
            "readme_sha256": sha256(v1_readme_path),
            "approval_boundary": {
                "approved": "research and controlled InfraSure integration testing",
                "pending": "recipient delivery pointer and dashboard promotion",
                "not_approved": [
                    "silent treatment of imputed factors as observed SCR",
                    "PML or TVaR scaling",
                    "automatic client-facing financial adjustment",
                ],
            },
        }
    )
    write_json(v1_manifest_path, v1_manifest)

    v2_manifest["publication_prefix"] = args.v2_publication_prefix.rstrip("/") + "/"
    v2_manifest["source_v1"]["gcs_prefix"] = v1_manifest["publication_prefix"]
    v2_manifest["nearest_fill_validation"] = v2_validation_path.name
    v2_manifest["nearest_fill_validation_sha256"] = sha256(v2_validation_path)
    write_json(v2_manifest_path, v2_manifest)

    print(
        json.dumps(
            {
                "status": "passed",
                "run_id": args.run_id,
                "v1_sha256": v1_manifest["output_sha256"],
                "v2_sha256": v2_manifest["output_sha256"],
                "v1_publication_prefix": v1_manifest["publication_prefix"],
                "v2_publication_prefix": v2_manifest["publication_prefix"],
            }
        )
    )


if __name__ == "__main__":
    main()

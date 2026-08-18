#!/usr/bin/env python3
"""Build the governed Solar overall-delta V2 candidate from immutable V1.

V2 preserves every V1 source/raw/fill field, updates the release schema label,
and appends a symmetric piecewise soft-log factor candidate. It does not alter
or overwrite V1 and does not claim financial calibration.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq


SCHEMA_VERSION = "scr_solar_overall_delta_v2"
SOURCE_SCHEMA_VERSION = "scr_solar_overall_delta_v1"
METHOD = "symmetric_piecewise_soft_log_arctan"
START = 3.0
CEILING = 5.0
FLOOR = 1 / CEILING
STATUS = "numerically_validated_financial_calibration_pending"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-parquet", required=True, type=Path)
    parser.add_argument("--source-manifest", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--run-id", required=True)
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def soft_upper(value: float) -> float:
    if value <= START:
        return value
    log_start = math.log(START)
    log_ceiling = math.log(CEILING)
    width = log_ceiling - log_start
    scaled_excess = (math.log(value) - log_start) / width
    bounded_excess = (2 / math.pi) * math.atan((math.pi / 2) * scaled_excess)
    return math.exp(log_start + width * bounded_excess)


def stabilize(value: float | None) -> float | None:
    if value is None:
        return None
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"Factor must be positive and finite; received {value}")
    if 1 / START <= value <= START:
        return value
    return soft_upper(value) if value > START else 1 / soft_upper(1 / value)


def append(table: pa.Table, name: str, values, data_type: pa.DataType) -> pa.Table:
    return table.append_column(name, pa.array(values, type=data_type))


def transform_column(values: list[float | None]) -> tuple[list[float | None], list[bool | None]]:
    transformed = []
    flags = []
    for value in values:
        candidate = stabilize(value)
        transformed.append(candidate)
        flags.append(
            None
            if value is None
            else not math.isclose(candidate, value, rel_tol=1e-12, abs_tol=1e-15)
        )
    return transformed, flags


def strict_monotonicity(values: list[float], transformed: list[float]) -> bool:
    pairs = sorted(set(zip(values, transformed)))
    return all(
        raw_right > raw_left and applied_right > applied_left
        for (raw_left, applied_left), (raw_right, applied_right) in zip(pairs, pairs[1:])
    )


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    source_manifest = json.loads(args.source_manifest.read_text(encoding="utf-8"))
    source_hash = sha256(args.source_parquet)
    if source_hash != source_manifest["output_sha256"]:
        raise ValueError("Source V1 Parquet does not match its manifest SHA-256")

    source = pq.read_table(args.source_parquet)
    source_rows = source.num_rows
    source_columns = source.column_names
    factor_raw = source["factor_raw"].to_pylist()
    factor_filled = source["factor_filled"].to_pylist()
    raw_candidate, raw_flags = transform_column(factor_raw)
    filled_candidate, filled_flags = transform_column(factor_filled)

    source_schema = source["schema_version"].to_pylist()
    if set(source_schema) != {SOURCE_SCHEMA_VERSION}:
        raise ValueError(f"Unexpected source schema values: {set(source_schema)}")
    schema_index = source.schema.get_field_index("schema_version")
    table = source.set_column(
        schema_index,
        "schema_version",
        pa.array([SCHEMA_VERSION] * source_rows, type=pa.string()),
    )
    table = append(table, "source_schema_version", source_schema, pa.string())
    table = append(table, "factor_raw_stabilized_candidate", raw_candidate, pa.float64())
    table = append(
        table,
        "percent_change_raw_stabilized_candidate",
        [None if value is None else value - 1 for value in raw_candidate],
        pa.float64(),
    )
    table = append(table, "factor_filled_stabilized_candidate", filled_candidate, pa.float64())
    table = append(
        table,
        "percent_change_filled_stabilized_candidate",
        [value - 1 for value in filled_candidate],
        pa.float64(),
    )
    table = append(table, "raw_factor_was_compressed", raw_flags, pa.bool_())
    table = append(table, "filled_factor_was_compressed", filled_flags, pa.bool_())
    table = append(table, "factor_stabilization_method", [METHOD] * source_rows, pa.string())
    table = append(table, "factor_stabilization_start", [START] * source_rows, pa.float64())
    table = append(table, "factor_stabilization_ceiling", [CEILING] * source_rows, pa.float64())
    table = append(table, "factor_stabilization_floor", [FLOOR] * source_rows, pa.float64())
    table = append(table, "factor_stabilization_status", [STATUS] * source_rows, pa.string())

    output_name = "scr_solar_conus_overall_delta_v2.parquet"
    output_path = args.output_dir / output_name
    pq.write_table(table, output_path, compression="zstd", use_dictionary=True, row_group_size=65536)

    raw_present = [(raw, applied) for raw, applied in zip(factor_raw, raw_candidate) if raw is not None]
    filled_present = list(zip(factor_filled, filled_candidate))
    raw_changed = sum(flag is True for flag in raw_flags)
    filled_changed = sum(filled_flags)
    filled_minimum = min(filled_candidate)
    filled_maximum = max(filled_candidate)
    raw_nulls = sum(value is None for value in raw_candidate)
    filled_nulls = sum(value is None for value in filled_candidate)
    identity_band_matches = all(
        applied == raw
        for raw, applied in filled_present
        if 1 / START <= raw <= START
    )
    checks = {
        "source_sha256_matches_manifest": True,
        "row_count_matches_v1": table.num_rows == source.num_rows,
        "source_columns_preserved": all(name in table.column_names for name in source_columns),
        "factor_raw_null_pattern_preserved": raw_nulls == source["factor_raw"].null_count,
        "factor_filled_candidate_has_no_nulls": filled_nulls == 0,
        "identity_band_exactly_preserved": identity_band_matches,
        "candidate_within_symmetric_bounds": filled_minimum >= FLOOR and filled_maximum <= CEILING,
        "transform_strictly_monotonic_raw": strict_monotonicity(
            [item[0] for item in raw_present], [item[1] for item in raw_present]
        ),
        "transform_strictly_monotonic_filled": strict_monotonicity(
            [item[0] for item in filled_present], [item[1] for item in filled_present]
        ),
        "v1_source_unchanged": sha256(args.source_parquet) == source_hash,
    }
    status = "passed" if all(checks.values()) else "failed"
    if status != "passed":
        raise ValueError(f"V2 QA failed: {checks}")

    output_hash = sha256(output_path)
    created_at = dt.datetime.now(dt.timezone.utc).isoformat()
    qa = {
        "status": status,
        "created_at_utc": created_at,
        "run_id": args.run_id,
        "row_count": table.num_rows,
        "column_count": table.num_columns,
        "raw_factor_null_count": raw_nulls,
        "filled_factor_null_count": filled_nulls,
        "raw_factor_compressed_rows": raw_changed,
        "raw_factor_compressed_share_of_observed_rows": raw_changed / len(raw_present),
        "filled_factor_compressed_rows": filled_changed,
        "filled_factor_compressed_share": filled_changed / table.num_rows,
        "raw_factor_range": [min(item[0] for item in raw_present), max(item[0] for item in raw_present)],
        "filled_candidate_range": [filled_minimum, filled_maximum],
        "checks": checks,
        "columns": table.column_names,
    }
    qa_path = args.output_dir / "qa_report.json"
    qa_path.write_text(json.dumps(qa, indent=2) + "\n", encoding="utf-8")

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "release_status": STATUS,
        "created_at_utc": created_at,
        "run_id": args.run_id,
        "output_file": output_name,
        "output_sha256": output_hash,
        "output_size_bytes": output_path.stat().st_size,
        "row_count": table.num_rows,
        "column_count": table.num_columns,
        "canonical_cell_count": source_manifest["canonical_cell_count"],
        "observed_cell_count": source_manifest["observed_cell_count"],
        "imputed_cell_count": source_manifest["imputed_cell_count"],
        "scenarios": source_manifest["scenarios"],
        "horizons": source_manifest["horizons"],
        "source_v1": {
            "local_file": str(args.source_parquet),
            "sha256": source_hash,
            "schema_version": source_manifest["schema_version"],
            "gcs_prefix": source_manifest.get("publication_prefix"),
        },
        "raw_factor_definition": source_manifest["factor_definition"],
        "candidate_field": "factor_filled_stabilized_candidate",
        "candidate_percent_change_field": "percent_change_filled_stabilized_candidate",
        "stabilization": {
            "method": METHOD,
            "start": START,
            "ceiling": CEILING,
            "floor": FLOOR,
            "identity_band": [1 / START, START],
            "formula": "piecewise arctangent compression in natural-log factor space; reciprocal below 1/start",
            "raw_factor_compressed_rows": raw_changed,
            "filled_factor_compressed_rows": filled_changed,
        },
        "approval_boundary": {
            "approved": "numerical screening candidate and GCS research delivery",
            "pending": "calibration against representative InfraSure EAL/TIV and review for Wind/Gas",
            "not_approved": ["PML scaling", "TVaR scaling", "client-facing automatic financial adjustment"],
        },
        "qa_report": qa_path.name,
        "qa_report_sha256": sha256(qa_path),
    }
    manifest_path = args.output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    readme = f"""# SCR Solar CONUS overall-delta V2 candidate

## What we started with

V1 contains `{source.num_rows:,}` rows for `{source_manifest['canonical_cell_count']:,}` canonical
cells, two SCR scenarios, and sixteen 2025–2100 horizons. Its overall factor is:

```text
factor_filled = |future adjustedTotalDamage| / |2025 adjustedTotalDamage|
```

V1 remains immutable. Its maximum raw factor is `{max(factor_filled):,.6f}×`.

## What V2 changes

V2 preserves the V1 raw, filled, imputation, donor, source, and location fields
and adds a numerically stabilized candidate factor:

```text
raw factor
    |
    +-- 0.333333× through 3× --> unchanged
    |
    +-- above 3× ------------> smooth arctangent log-space compression toward 5×
    |
    +-- below 0.333333× ------> reciprocal compression toward 0.20×
```

Primary candidate field:

```text
factor_filled_stabilized_candidate
```

Raw and filled factors remain available and are never overwritten.

## What this release provides

| Item | Value |
|---|---:|
| Rows | {table.num_rows:,} |
| Canonical cells | {source_manifest['canonical_cell_count']:,} |
| Raw observed rows compressed | {raw_changed:,} |
| Complete-grid rows compressed | {filled_changed:,} |
| Candidate minimum | {filled_minimum:.6f}× |
| Candidate maximum | {filled_maximum:.6f}× |
| QA status | `{status}` |

The candidate changes only the extreme tail while exactly preserving the
`0.333333×–3×` identity band and the ordering of distinct factor values.

## Status and permitted use

This is a **numerically validated screening candidate**. It is suitable for
InfraSure integration testing against expected-loss/EAL fields while retaining
the raw factor and audit flags.

It is not yet approved for:

- automatic client-facing financial adjustment;
- PML or TVaR scaling; or
- universal use across Wind and Gas before their distributions are tested.

The 3× start, 5× ceiling, and 0.20× reciprocal floor are explicit policy
parameters. Final financial approval requires representative EAL/TIV testing.

## Key columns

| Column | Meaning |
|---|---|
| `factor_raw` | Observed-cell V1 ratio; null for source-missing cells |
| `factor_filled` | Complete-grid V1 ratio after nearest observed-cell fill |
| `factor_raw_stabilized_candidate` | Stabilized observed-cell candidate |
| `factor_filled_stabilized_candidate` | Stabilized complete-grid candidate |
| `raw_factor_was_compressed` | Whether the raw observed factor changed |
| `filled_factor_was_compressed` | Whether the complete-grid factor changed |
| `factor_stabilization_status` | Approval boundary for the candidate |

## Validation

See `qa_report.json` for bounds, null behavior, source parity, identity-band,
monotonicity, row-count, and checksum checks. See `manifest.json` for immutable
source and release identifiers.
"""
    (args.output_dir / "README.md").write_text(readme, encoding="utf-8")

    # README is part of the delivery; refresh its checksum after it exists.
    manifest["readme"] = "README.md"
    manifest["readme_sha256"] = sha256(args.output_dir / "README.md")
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": status,
                "rows": table.num_rows,
                "columns": table.num_columns,
                "raw_changed": raw_changed,
                "filled_changed": filled_changed,
                "output_sha256": output_hash,
                "output_dir": str(args.output_dir),
            }
        )
    )


if __name__ == "__main__":
    main()

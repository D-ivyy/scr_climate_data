#!/usr/bin/env python3
"""Build a governed SCR overall-delta V2 candidate from immutable V1.

V2 preserves every V1 source/raw/fill field, updates the release schema label,
and appends a symmetric piecewise soft-log factor candidate. It does not alter
or overwrite V1 and does not claim financial calibration. The historical Solar
CLI remains the default; asset-specific names and schema labels are configurable.
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


DEFAULT_SCHEMA_VERSION = "scr_solar_overall_delta_v2"
DEFAULT_SOURCE_SCHEMA_VERSION = "scr_solar_overall_delta_v1"
METHOD = "symmetric_piecewise_soft_log_arctan"
DEFAULT_START = 3.0
DEFAULT_CEILING = 5.0
DEFAULT_STATUS = "numerically_validated_financial_calibration_pending"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-parquet", required=True, type=Path)
    parser.add_argument("--source-manifest", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--output-name", default="scr_solar_conus_overall_delta_v2.parquet")
    parser.add_argument("--schema-version", default=DEFAULT_SCHEMA_VERSION)
    parser.add_argument("--source-schema-version", default=DEFAULT_SOURCE_SCHEMA_VERSION)
    parser.add_argument("--asset-label", default="Solar")
    parser.add_argument("--start", type=float, default=DEFAULT_START)
    parser.add_argument("--ceiling", type=float, default=DEFAULT_CEILING)
    parser.add_argument("--status", default=DEFAULT_STATUS)
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def soft_upper(value: float, start: float, ceiling: float) -> float:
    if value <= start:
        return value
    log_start = math.log(start)
    log_ceiling = math.log(ceiling)
    width = log_ceiling - log_start
    scaled_excess = (math.log(value) - log_start) / width
    bounded_excess = (2 / math.pi) * math.atan((math.pi / 2) * scaled_excess)
    return math.exp(log_start + width * bounded_excess)


def stabilize(value: float | None, *, start: float, ceiling: float) -> float | None:
    if value is None:
        return None
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"Factor must be positive and finite; received {value}")
    if 1 / start <= value <= start:
        return value
    return (
        soft_upper(value, start, ceiling)
        if value > start
        else 1 / soft_upper(1 / value, start, ceiling)
    )


def append(table: pa.Table, name: str, values, data_type: pa.DataType) -> pa.Table:
    return table.append_column(name, pa.array(values, type=data_type))


def transform_column(
    values: list[float | None], *, start: float, ceiling: float
) -> tuple[list[float | None], list[bool | None]]:
    transformed = []
    flags = []
    for value in values:
        candidate = stabilize(value, start=start, ceiling=ceiling)
        transformed.append(candidate)
        flags.append(
            None
            if value is None
            else not math.isclose(candidate, value, rel_tol=1e-12, abs_tol=1e-15)
        )
    return transformed, flags


def strict_monotonicity(values: list[float], transformed: list[float]) -> bool:
    pairs = sorted(set(zip(values, transformed)))
    for (raw_left, applied_left), (raw_right, applied_right) in zip(pairs, pairs[1:]):
        same_raw = math.isclose(raw_left, raw_right, rel_tol=1e-12, abs_tol=1e-15)
        if same_raw:
            if not math.isclose(
                applied_left, applied_right, rel_tol=1e-12, abs_tol=1e-15
            ):
                return False
        elif not applied_right > applied_left:
            return False
    return True


def main() -> None:
    args = parse_args()
    if not (1 < args.start < args.ceiling):
        raise ValueError("Expected 1 < start < ceiling")
    floor = 1 / args.ceiling
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
    raw_candidate, raw_flags = transform_column(
        factor_raw, start=args.start, ceiling=args.ceiling
    )
    filled_candidate, filled_flags = transform_column(
        factor_filled, start=args.start, ceiling=args.ceiling
    )

    source_schema = source["schema_version"].to_pylist()
    if set(source_schema) != {args.source_schema_version}:
        raise ValueError(f"Unexpected source schema values: {set(source_schema)}")
    schema_index = source.schema.get_field_index("schema_version")
    table = source.set_column(
        schema_index,
        "schema_version",
        pa.array([args.schema_version] * source_rows, type=pa.string()),
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
        [None if value is None else value - 1 for value in filled_candidate],
        pa.float64(),
    )
    table = append(table, "raw_factor_was_compressed", raw_flags, pa.bool_())
    table = append(table, "filled_factor_was_compressed", filled_flags, pa.bool_())
    table = append(table, "factor_stabilization_method", [METHOD] * source_rows, pa.string())
    table = append(table, "factor_stabilization_start", [args.start] * source_rows, pa.float64())
    table = append(table, "factor_stabilization_ceiling", [args.ceiling] * source_rows, pa.float64())
    table = append(table, "factor_stabilization_floor", [floor] * source_rows, pa.float64())
    table = append(table, "factor_stabilization_status", [args.status] * source_rows, pa.string())

    output_name = args.output_name
    output_path = args.output_dir / output_name
    pq.write_table(table, output_path, compression="zstd", use_dictionary=True, row_group_size=65536)

    raw_present = [(raw, applied) for raw, applied in zip(factor_raw, raw_candidate) if raw is not None]
    filled_present = [
        (raw, applied)
        for raw, applied in zip(factor_filled, filled_candidate)
        if raw is not None
    ]
    raw_changed = sum(flag is True for flag in raw_flags)
    filled_changed = sum(flag is True for flag in filled_flags)
    filled_minimum = min(item[1] for item in filled_present)
    filled_maximum = max(item[1] for item in filled_present)
    raw_nulls = sum(value is None for value in raw_candidate)
    filled_nulls = sum(value is None for value in filled_candidate)
    identity_band_matches = all(
        applied == raw
        for raw, applied in filled_present
        if 1 / args.start <= raw <= args.start
    )
    checks = {
        "source_sha256_matches_manifest": True,
        "row_count_matches_v1": table.num_rows == source.num_rows,
        "source_columns_preserved": all(name in table.column_names for name in source_columns),
        "factor_raw_null_pattern_preserved": raw_nulls == source["factor_raw"].null_count,
        "factor_filled_null_pattern_preserved": (
            filled_nulls == source["factor_filled"].null_count
        ),
        "identity_band_exactly_preserved": identity_band_matches,
        "candidate_within_symmetric_bounds": (
            filled_minimum >= floor and filled_maximum <= args.ceiling
        ),
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
        "schema_version": args.schema_version,
        "release_status": args.status,
        "created_at_utc": created_at,
        "run_id": args.run_id,
        "output_file": output_name,
        "output_sha256": output_hash,
        "output_size_bytes": output_path.stat().st_size,
        "row_count": table.num_rows,
        "column_count": table.num_columns,
        "canonical_cell_count": source_manifest["canonical_cell_count"],
        "observed_cell_count": source_manifest["observed_cell_count"],
        "metric_eligible_cell_count": source_manifest.get("metric_eligible_cell_count"),
        "metric_unavailable_cell_count": source_manifest.get("metric_unavailable_cell_count"),
        "missing_source_cell_count": source_manifest.get("missing_source_cell_count"),
        "imputed_cell_count": source_manifest["imputed_cell_count"],
        "factor_filled_null_count": filled_nulls,
        "missing_cell_method": source_manifest.get("missing_cell_method"),
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
            "start": args.start,
            "ceiling": args.ceiling,
            "floor": floor,
            "identity_band": [1 / args.start, args.start],
            "formula": "piecewise arctangent compression in natural-log factor space; reciprocal below 1/start",
            "raw_factor_compressed_rows": raw_changed,
            "filled_factor_compressed_rows": filled_changed,
        },
        "approval_boundary": {
            "approved": "numerical screening candidate and GCS research delivery",
            "pending": f"calibration against representative InfraSure {args.asset_label} EAL/TIV",
            "not_approved": ["PML scaling", "TVaR scaling", "client-facing automatic financial adjustment"],
        },
        "qa_report": qa_path.name,
        "qa_report_sha256": sha256(qa_path),
    }
    manifest_path = args.output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    readme = f"""# SCR {args.asset_label} CONUS overall-delta V2 candidate

## What we started with

V1 contains `{source.num_rows:,}` rows for `{source_manifest['canonical_cell_count']:,}` canonical
cells, two SCR scenarios, and sixteen 2025–2100 horizons. Its overall factor is:

```text
factor_filled = |future adjustedTotalDamage| / |2025 adjustedTotalDamage|
```

V1 remains immutable. Its maximum available raw factor is
`{max(value for value in factor_filled if value is not None):,.6f}×`.

## What V2 changes

V2 preserves the V1 raw, filled, imputation, donor, source, and location fields
and adds a numerically stabilized candidate factor:

```text
raw factor
    |
    +-- {1 / args.start:.6f}× through {args.start:g}× --> unchanged
    |
    +-- above {args.start:g}× ------------> smooth arctangent log-space compression toward {args.ceiling:g}×
    |
    +-- below {1 / args.start:.6f}× ------> reciprocal compression toward {floor:.2f}×
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
| Candidate null rows preserved | {filled_nulls:,} |
| Candidate minimum | {filled_minimum:.6f}× |
| Candidate maximum | {filled_maximum:.6f}× |
| QA status | `{status}` |

The candidate changes only the extreme tail while exactly preserving the
`{1 / args.start:.6f}×–{args.start:g}×` identity band and the ordering of distinct
factor values. Null source factors remain null; stabilization does not fill or
reinterpret them.

## Status and permitted use

This is a **numerically validated screening candidate**. It is suitable for
InfraSure integration testing against expected-loss/EAL fields while retaining
the raw factor and audit flags.

It is not yet approved for:

- automatic client-facing financial adjustment;
- PML or TVaR scaling; or
- use for another asset class before its distribution is tested.

The {args.start:g}× start, {args.ceiling:g}× ceiling, and {floor:.2f}× reciprocal floor are explicit policy
parameters. Final financial approval requires representative EAL/TIV testing.

## Key columns

| Column | Meaning |
|---|---|
| `factor_raw` | Source-derived V1 ratio; null when the baseline/future path is unsupported |
| `factor_filled` | V1 applied/fill input; may remain null under a retain-null policy |
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

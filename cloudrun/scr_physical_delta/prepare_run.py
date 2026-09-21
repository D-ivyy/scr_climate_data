#!/usr/bin/env python3
"""Freeze and optionally stage one SCR physical-risk Cloud Run inventory."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import subprocess
from pathlib import Path


CELL_ID_RE = re.compile(r"Cell_(\d+)_")
CHUNK_SIZE = 200


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-prefix", required=True)
    parser.add_argument("--staging-prefix", required=True)
    parser.add_argument("--inventory-output", required=True, type=Path)
    parser.add_argument("--asset-type", required=True)
    parser.add_argument("--ticcs-subclass", required=True)
    parser.add_argument(
        "--stage",
        action="store_true",
        help="Copy source workbooks to the immutable staging prefix before writing inventory.",
    )
    return parser.parse_args()


def run_text(args: list[str]) -> str:
    return subprocess.check_output(args, text=True)


def sha256_lines(values: list[str]) -> str:
    payload = "".join(f"{value}\n" for value in values).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def main() -> None:
    args = parse_args()
    source_prefix = args.source_prefix.rstrip("/") + "/"
    staging_prefix = args.staging_prefix.rstrip("/") + "/"
    if "run_id=" not in staging_prefix:
        raise ValueError("Staging prefix must be run-specific and contain run_id=")

    output = run_text(
        ["gcloud", "storage", "ls", "--recursive", f"{source_prefix}**"]
    )
    source_uris = sorted(
        line.strip() for line in output.splitlines() if line.strip().endswith(".xlsx")
    )
    if not source_uris:
        raise ValueError(f"No XLSX workbooks found under {source_prefix}")

    filenames = [Path(uri).name for uri in source_uris]
    if len(filenames) != len(set(filenames)):
        raise ValueError("Source inventory contains duplicate basenames")
    cell_ids = []
    for uri in source_uris:
        match = CELL_ID_RE.search(uri)
        if not match:
            raise ValueError(f"Could not parse cell ID from {uri}")
        cell_ids.append(int(match.group(1)))
    if len(cell_ids) != len(set(cell_ids)):
        raise ValueError("Source inventory contains duplicate cell IDs")

    staged_uris = [f"{staging_prefix}{filename}" for filename in filenames]
    if args.stage:
        for offset in range(0, len(source_uris), CHUNK_SIZE):
            chunk = source_uris[offset : offset + CHUNK_SIZE]
            completed = subprocess.run(
                [
                    "gcloud",
                    "--quiet",
                    "storage",
                    "cp",
                    "--if-generation-match=0",
                    *chunk,
                    staging_prefix,
                ],
                text=True,
                capture_output=True,
            )
            if completed.returncode:
                detail = (completed.stderr or completed.stdout)[-4000:]
                raise RuntimeError(
                    f"Staging failed for source offset {offset}: {detail}"
                )
            print(
                json.dumps(
                    {
                        "staged": min(offset + len(chunk), len(source_uris)),
                        "total": len(source_uris),
                    }
                ),
                flush=True,
            )

    inventory = {
        "schema_version": "scr_physical_source_inventory_v1",
        "created_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "asset_type": args.asset_type,
        "ticcs_subclass": args.ticcs_subclass,
        "source_prefix": source_prefix,
        "staging_prefix": staging_prefix if args.stage else None,
        "source_file_count": len(source_uris),
        "unique_cell_count": len(set(cell_ids)),
        "source_uri_list_sha256": sha256_lines(source_uris),
        "effective_uri_list_sha256": sha256_lines(staged_uris if args.stage else source_uris),
        "original_uris": source_uris,
        "uris": staged_uris if args.stage else source_uris,
    }
    args.inventory_output.parent.mkdir(parents=True, exist_ok=True)
    args.inventory_output.write_text(json.dumps(inventory, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "inventory": str(args.inventory_output),
                "files": len(source_uris),
                "cells": len(set(cell_ids)),
                "source_uri_list_sha256": inventory["source_uri_list_sha256"],
                "effective_uri_list_sha256": inventory["effective_uri_list_sha256"],
            }
        )
    )


if __name__ == "__main__":
    main()

# ---
# jupyter:
#   jupytext:
#     formats: ipynb,py:percent
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.19.3
#   kernelspec:
#     display_name: Python 3
#     language: python
#     name: python3
# ---

# %% [markdown]
# # SCR Solar CONUS: bucket and canonical-grid inventory
#
# This notebook performs a metadata-only audit. It does not download or transform
# the 1.8 GiB workbook corpus. Its job is to prove whether the SCR filenames use
# the same cell identity contract as InfraSure's canonical 13,085-cell grid and
# to make missing source coverage explicit.

# %%
from __future__ import annotations

import csv
import json
import os
import re
import subprocess
from collections import Counter, deque
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = next(
    (
        candidate
        for candidate in (Path.cwd(), *Path.cwd().parents)
        if (candidate / "docs" / "scr_profile").exists()
    ),
    Path(os.environ.get("SCR_REPO_ROOT", Path.cwd())),
)

HAZARD_MODELING_ROOT = Path(
    os.environ.get(
        "HAZARD_MODELING_ROOT",
        "/Users/divy/code/work/infrasure_git_codes/Hazard_modeling",
    )
)
GRID_PATH = Path(
    os.environ.get(
        "SCR_CANONICAL_GRID",
        HAZARD_MODELING_ROOT
        / "data/hazard_conus_grid/common/benchmark_grid/served_conus_cell_ids_v2026_06.csv",
    )
)
BUCKET_GLOB = os.environ.get(
    "SCR_BUCKET_GLOB",
    "gs://infrasure-scr-data/physical_risks_exports/**",
)
RUN_DATE = os.environ.get("SCR_INVESTIGATION_DATE", "2026-08-18")
OUTPUT_DIR = REPO_ROOT / "notebooks/conus_solar_physical_delta/outputs" / RUN_DATE
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

FILENAME_PATTERN = re.compile(
    r"^CONUS13K_Cell_(?P<cell_id>\d+)_(?P<state>[A-Z]{2})_"
    r"(?:.+?)_(?P<asset>SolarPV)_physical_risks\.xlsx$"
)


def quantile(values: list[int], probability: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


# %% [markdown]
# ## Load the canonical grid and list the source bucket

# %%
with GRID_PATH.open(newline="", encoding="utf-8-sig") as handle:
    grid_rows = list(csv.DictReader(handle))

listing = subprocess.run(
    ["gsutil", "ls", "-l", BUCKET_GLOB],
    check=True,
    capture_output=True,
    text=True,
).stdout.splitlines()

objects: list[dict[str, object]] = []
unparsed: list[str] = []
for line in listing:
    listing_match = re.match(r"^\s*(\d+)\s+(\S+)\s+(gs://\S+)$", line)
    if not listing_match:
        continue
    size, updated, uri = listing_match.groups()
    filename_match = FILENAME_PATTERN.match(uri.rsplit("/", 1)[-1])
    if not filename_match:
        unparsed.append(uri)
        continue
    objects.append(
        {
            **filename_match.groupdict(),
            "cell_id": int(filename_match.group("cell_id")),
            "size_bytes": int(size),
            "updated": updated,
            "uri": uri,
        }
    )

grid_by_id = {int(row["cell_id"]): row for row in grid_rows}
grid_ids = set(grid_by_id)
object_ids = [int(row["cell_id"]) for row in objects]
object_id_set = set(object_ids)
missing_ids = sorted(grid_ids - object_id_set)
extra_ids = sorted(object_id_set - grid_ids)
duplicate_ids = sorted(cell_id for cell_id, count in Counter(object_ids).items() if count > 1)


# %% [markdown]
# ## Reconcile the embedded state label

# %%
state_mismatches = []
for row in objects:
    cell_id = int(row["cell_id"])
    grid_row = grid_by_id.get(cell_id)
    if not grid_row:
        continue
    if row["state"] != grid_row["state_abbr"]:
        state_mismatches.append([cell_id, row["state"], grid_row["state_abbr"]])

missing_by_state = Counter(grid_by_id[cell_id]["state_abbr"] for cell_id in missing_ids)
served_by_state = Counter(row["state_abbr"] for row in grid_rows)
missing_state_rates = [
    {
        "state": state,
        "missing": missing_by_state[state],
        "served": served_by_state[state],
        "missing_rate": missing_by_state[state] / served_by_state[state],
    }
    for state in sorted(served_by_state)
]
missing_state_rates.sort(key=lambda row: (-row["missing_rate"], -row["missing"], row["state"]))


# %% [markdown]
# ## Measure whether missing cells are isolated or spatially clustered

# %%
missing_coordinates = {
    (int(grid_by_id[cell_id]["lat_idx"]), int(grid_by_id[cell_id]["lon_idx"])): cell_id
    for cell_id in missing_ids
}
unseen = set(missing_coordinates)
component_sizes: list[int] = []
while unseen:
    seed = unseen.pop()
    queue = deque([seed])
    component_size = 0
    while queue:
        lat_idx, lon_idx = queue.popleft()
        component_size += 1
        for neighbor in (
            (lat_idx - 1, lon_idx),
            (lat_idx + 1, lon_idx),
            (lat_idx, lon_idx - 1),
            (lat_idx, lon_idx + 1),
        ):
            if neighbor in unseen:
                unseen.remove(neighbor)
                queue.append(neighbor)
    component_sizes.append(component_size)
component_sizes.sort(reverse=True)


# %% [markdown]
# ## Select a deterministic workbook sample for schema inspection

# %%
ordered_by_id = sorted(objects, key=lambda row: int(row["cell_id"]))
positions = [
    0,
    len(ordered_by_id) // 10,
    len(ordered_by_id) // 5,
    3 * len(ordered_by_id) // 10,
    2 * len(ordered_by_id) // 5,
    len(ordered_by_id) // 2,
    3 * len(ordered_by_id) // 5,
    7 * len(ordered_by_id) // 10,
    4 * len(ordered_by_id) // 5,
    9 * len(ordered_by_id) // 10,
    len(ordered_by_id) - 1,
]
sample_candidates = [ordered_by_id[position] for position in positions]
sample_candidates.extend(sorted(objects, key=lambda row: int(row["size_bytes"]))[:3])
sample_candidates.extend(
    sorted(objects, key=lambda row: int(row["size_bytes"]), reverse=True)[:3]
)
sample_by_id = {int(row["cell_id"]): row for row in sample_candidates}

sizes = [int(row["size_bytes"]) for row in objects]
summary = {
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "bucket_glob": BUCKET_GLOB,
    "canonical_grid_path": str(GRID_PATH),
    "canonical_grid_rows": len(grid_rows),
    "parsed_workbooks": len(objects),
    "unparsed_objects": len(unparsed),
    "unique_workbook_cell_ids": len(object_id_set),
    "duplicate_cell_ids": len(duplicate_ids),
    "missing_canonical_cells": len(missing_ids),
    "extra_noncanonical_cells": len(extra_ids),
    "coverage_rate": len(object_id_set & grid_ids) / len(grid_ids),
    "state_label_mismatches": len(state_mismatches),
    "object_size_bytes": {
        "min": min(sizes),
        "p01": quantile(sizes, 0.01),
        "p50": quantile(sizes, 0.50),
        "p99": quantile(sizes, 0.99),
        "max": max(sizes),
        "total": sum(sizes),
    },
    "missing_components": {
        "count": len(component_sizes),
        "largest_20": component_sizes[:20],
        "singletons": sum(size == 1 for size in component_sizes),
    },
    "missing_by_state": missing_state_rates,
    "duplicate_id_sample": duplicate_ids[:20],
    "extra_id_sample": extra_ids[:20],
    "missing_id_sample": missing_ids[:20],
    "unparsed_sample": unparsed[:20],
    "state_mismatch_sample": state_mismatches[:20],
    "workbook_sample": [sample_by_id[cell_id] for cell_id in sorted(sample_by_id)],
}

with (OUTPUT_DIR / "bucket_grid_inventory.json").open("w", encoding="utf-8") as handle:
    json.dump(summary, handle, indent=2)

with (OUTPUT_DIR / "missing_cell_ids.csv").open("w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(
        handle,
        fieldnames=["cell_id", "lat_idx", "lon_idx", "lat_center", "lon_center", "state_abbr"],
        extrasaction="ignore",
        lineterminator="\n",
    )
    writer.writeheader()
    writer.writerows(grid_by_id[cell_id] for cell_id in missing_ids)

with (OUTPUT_DIR / "missing_cells_by_state.csv").open("w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(
        handle,
        fieldnames=["state", "missing", "served", "missing_rate"],
        lineterminator="\n",
    )
    writer.writeheader()
    writer.writerows(missing_state_rates)

summary_view = {
    key: summary[key]
    for key in (
        "canonical_grid_rows",
        "parsed_workbooks",
        "unique_workbook_cell_ids",
        "missing_canonical_cells",
        "coverage_rate",
        "duplicate_cell_ids",
        "extra_noncanonical_cells",
        "state_label_mismatches",
        "missing_components",
    )
}
summary_view

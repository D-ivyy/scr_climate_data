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
# # SCR Solar CONUS: sampled workbook schema and delta availability
#
# This notebook downloads only the deterministic sample selected by notebook 00.
# It uses `@oai/artifact-tool` to read the XLSX files, verifies workbook coordinates
# against the canonical grid, and tests whether 2025-to-future physical-damage
# factors can actually be computed. Sample findings are evidence for parser design,
# not national coverage estimates.

# %%
from __future__ import annotations

import csv
import json
import math
import os
import re
import statistics
import subprocess
from collections import Counter
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
RUN_DATE = os.environ.get("SCR_INVESTIGATION_DATE", "2026-08-18")
OUTPUT_DIR = REPO_ROOT / "notebooks/conus_solar_physical_delta/outputs" / RUN_DATE
INVENTORY_PATH = OUTPUT_DIR / "bucket_grid_inventory.json"
SAMPLE_DIR = Path(os.environ.get("SCR_SAMPLE_DIR", f"/tmp/scr_climate_data_{RUN_DATE.replace('-', '')}_sample"))
RAW_ARTIFACT_OUTPUT = SAMPLE_DIR / "artifact_tool_sample.json"
NODE_BIN = os.environ.get(
    "SCR_NODE_BIN",
    "/Users/divy/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node",
)
NODE_MODULES = os.environ.get(
    "SCR_NODE_MODULES",
    "/Users/divy/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules",
)
INSPECTOR = REPO_ROOT / "notebooks/conus_solar_physical_delta/support/inspect_workbooks.mjs"

if not INVENTORY_PATH.exists():
    raise FileNotFoundError(f"Run notebook 00 first; missing {INVENTORY_PATH}")

with INVENTORY_PATH.open(encoding="utf-8") as handle:
    inventory = json.load(handle)
with GRID_PATH.open(newline="", encoding="utf-8-sig") as handle:
    grid_by_id = {int(row["cell_id"]): row for row in csv.DictReader(handle)}


# %% [markdown]
# ## Download the deterministic sample and read it with artifact-tool

# %%
SAMPLE_DIR.mkdir(parents=True, exist_ok=True)
for item in inventory["workbook_sample"]:
    target = SAMPLE_DIR / Path(item["uri"]).name
    if not target.exists():
        subprocess.run(["gsutil", "cp", item["uri"], str(target)], check=True)

environment = os.environ.copy()
environment["SCR_NODE_MODULES"] = NODE_MODULES
subprocess.run(
    [NODE_BIN, str(INSPECTOR), str(SAMPLE_DIR), str(RAW_ARTIFACT_OUTPUT)],
    check=True,
    env=environment,
)
with RAW_ARTIFACT_OUTPUT.open(encoding="utf-8") as handle:
    extracted = json.load(handle)
files = extracted["files"]


# %% [markdown]
# ## Check grid-center coordinates and structural consistency

# %%
coordinate_pattern = re.compile(r"\(\s*([-+0-9.eE]+)\s*,\s*([-+0-9.eE]+)\s*\)")
coordinate_checks = []
for workbook in files:
    cell_id = workbook["cellId"]
    grid_row = grid_by_id[cell_id]
    if len(workbook["coordinates"]) != 1:
        raise ValueError(f"Expected one coordinate in {workbook['filename']}")
    match = coordinate_pattern.fullmatch(workbook["coordinates"][0])
    if not match:
        raise ValueError(f"Unexpected coordinate format in {workbook['filename']}")
    latitude, longitude = map(float, match.groups())
    coordinate_checks.append(
        {
            "cell_id": cell_id,
            "workbook_lat": latitude,
            "workbook_lon": longitude,
            "grid_lat": float(grid_row["lat_center"]),
            "grid_lon": float(grid_row["lon_center"]),
            "exact_match": latitude == float(grid_row["lat_center"])
            and longitude == float(grid_row["lon_center"]),
        }
    )

schema_variants = Counter(json.dumps(workbook["headers"]) for workbook in files)
row_counts = sorted({workbook["rowCount"] for workbook in files})
column_counts = sorted({workbook["columnCount"] for workbook in files})
output_ranges = sorted({workbook["outputRange"] for workbook in files})
scenario_variants = Counter(json.dumps(workbook["scenarios"]) for workbook in files)
horizon_variants = Counter(json.dumps(workbook["horizons"]) for workbook in files)
hazard_variants = Counter(json.dumps(workbook["hazards"]) for workbook in files)


# %% [markdown]
# ## Measure physical-damage factor availability

# %%
SCENARIOS = ("ssp2-4.5", "ssp5-8.5")
FUTURE_HORIZONS = ("2050", "2100")
HAZARDS = sorted({hazard for workbook in files for hazard in workbook["hazards"]})


def value_at(workbook: dict, scenario: str, horizon: str, scope: str, hazard: str | None = None):
    horizon_record = workbook["grouped"].get(scenario, {}).get(horizon)
    if horizon_record is None:
        return None
    if scope == "overall":
        return horizon_record["total"].get("adjustedTotalDamage")
    return horizon_record["hazards"].get(hazard, {}).get("adjustedHazardDamage")


def usable_factor(baseline, future) -> bool:
    return baseline is not None and future is not None and not math.isclose(abs(baseline), 0.0)


availability_rows = []
factor_distributions = []
for scope, hazard in [("overall", None), *[("hazard", hazard) for hazard in HAZARDS]]:
    for scenario in SCENARIOS:
        for horizon in FUTURE_HORIZONS:
            values = []
            for workbook in files:
                baseline = value_at(workbook, scenario, "2025", scope, hazard)
                future = value_at(workbook, scenario, horizon, scope, hazard)
                if usable_factor(baseline, future):
                    values.append(abs(future) / abs(baseline))
            availability_rows.append(
                {
                    "scope": scope,
                    "hazard": hazard or "Overall",
                    "scenario": scenario,
                    "horizon": horizon,
                    "valid_factor_files": len(values),
                    "sample_files": len(files),
                }
            )
            factor_distributions.append(
                {
                    "scope": scope,
                    "hazard": hazard or "Overall",
                    "scenario": scenario,
                    "horizon": horizon,
                    "n": len(values),
                    "minimum": min(values) if values else None,
                    "median": statistics.median(values) if values else None,
                    "maximum": max(values) if values else None,
                }
            )

raw_adjusted = Counter()
for workbook in files:
    for pair, counts in workbook["rawAdjusted"].items():
        raw_adjusted[(pair, "pairs")] += counts["pairs"]
        raw_adjusted[(pair, "equal")] += counts["equal"]
        raw_adjusted[(pair, "different")] += counts["different"]

total_reconciliation = {"tested": 0, "matched": 0, "mismatched": 0}
for workbook in files:
    for scenario in SCENARIOS:
        for horizon in (str(year) for year in range(2025, 2101, 5)):
            horizon_record = workbook["grouped"][scenario][horizon]
            total_damage = horizon_record["total"].get("adjustedTotalDamage")
            hazard_values = [
                metrics.get("adjustedHazardDamage")
                for metrics in horizon_record["hazards"].values()
            ]
            hazard_values = [value for value in hazard_values if value is not None]
            if total_damage is None or not hazard_values:
                continue
            total_reconciliation["tested"] += 1
            if math.isclose(total_damage, sum(hazard_values), rel_tol=0.0, abs_tol=1e-12):
                total_reconciliation["matched"] += 1
            else:
                total_reconciliation["mismatched"] += 1


# %% [markdown]
# ## Preserve one readable factor example

# %%
preferred_example_id = 335196
example_workbook = next(
    (workbook for workbook in files if workbook["cellId"] == preferred_example_id),
    files[0],
)
example_rows = []
for scope, hazard in [
    ("overall", None),
    ("hazard", "Flood"),
    ("hazard", "Wind"),
    ("hazard", "Wildfire"),
]:
    for scenario in SCENARIOS:
        baseline = value_at(example_workbook, scenario, "2025", scope, hazard)
        for horizon in FUTURE_HORIZONS:
            future = value_at(example_workbook, scenario, horizon, scope, hazard)
            example_rows.append(
                {
                    "cell_id": example_workbook["cellId"],
                    "scope": scope,
                    "hazard": hazard or "Overall",
                    "scenario": scenario,
                    "baseline_year": 2025,
                    "horizon": int(horizon),
                    "baseline_damage": baseline,
                    "future_damage": future,
                    "absolute_change_magnitude": (
                        abs(future) - abs(baseline)
                        if baseline is not None and future is not None
                        else None
                    ),
                    "raw_factor": (
                        abs(future) / abs(baseline)
                        if usable_factor(baseline, future)
                        else None
                    ),
                }
            )


# %% [markdown]
# ## Write lightweight evidence outputs

# %%
summary = {
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "sample_method": "deterministic geographic deciles plus smallest/largest workbook sizes",
    "sample_files": len(files),
    "exact_coordinate_matches": sum(row["exact_match"] for row in coordinate_checks),
    "schema_variants": len(schema_variants),
    "row_counts": row_counts,
    "column_counts": column_counts,
    "output_ranges": output_ranges,
    "scenario_variants": len(scenario_variants),
    "horizon_variants": len(horizon_variants),
    "hazard_variants": len(hazard_variants),
    "scenarios": files[0]["scenarios"],
    "horizons": files[0]["horizons"],
    "hazards": files[0]["hazards"],
    "asset_type": files[0]["ticcsSubClassName"],
    "asset_ticcs_subclass": files[0]["ticcsSubClass"],
    "raw_adjusted_comparisons": {
        pair: {
            "pairs": raw_adjusted[(pair, "pairs")],
            "equal": raw_adjusted[(pair, "equal")],
            "different": raw_adjusted[(pair, "different")],
        }
        for pair, _ in sorted({key for key in raw_adjusted})
    },
    "total_damage_reconciliation": total_reconciliation,
    "factor_distributions": factor_distributions,
}

with (OUTPUT_DIR / "sample_workbook_validation.json").open("w", encoding="utf-8") as handle:
    json.dump(summary, handle, indent=2)

with (OUTPUT_DIR / "sample_metric_availability.csv").open("w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(
        handle,
        fieldnames=list(availability_rows[0]),
        lineterminator="\n",
    )
    writer.writeheader()
    writer.writerows(availability_rows)

with (OUTPUT_DIR / "sample_delta_examples.csv").open("w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(
        handle,
        fieldnames=list(example_rows[0]),
        lineterminator="\n",
    )
    writer.writeheader()
    writer.writerows(example_rows)

summary

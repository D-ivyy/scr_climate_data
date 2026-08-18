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
# # Full Solar CONUS overall-delta distribution
#
# This notebook consumes artifact-tool extraction shards produced from the 11,928
# SCR workbooks. It derives the raw overall multiplier from `adjustedTotalDamage`,
# summarizes every five-year horizon, and produces selected-horizon distribution
# and spatial plots. It does not apply a cap, compression, or missing-cell fill.

# %%
from __future__ import annotations

import csv
import json
import math
import os
import statistics
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import matplotlib.pyplot as plt


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
SHARD_DIR = Path(os.environ.get("SCR_FULL_SHARD_DIR", "/tmp/scr_full_shards"))
RUN_DATE = os.environ.get("SCR_INVESTIGATION_DATE", "2026-08-18")
OUTPUT_DIR = REPO_ROOT / "notebooks/conus_solar_physical_delta/outputs" / RUN_DATE
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

SCENARIOS = ("ssp2-4.5", "ssp5-8.5")
HORIZONS = tuple(str(year) for year in range(2025, 2101, 5))
SELECTED_HORIZONS = ("2035", "2040", "2050", "2100")


def quantile(values: list[float], probability: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


# %% [markdown]
# ## Merge extraction shards and join the canonical grid

# %%
shard_paths = sorted(SHARD_DIR.glob("shard_*.json"))
if not shard_paths:
    raise FileNotFoundError(f"No extraction shards found under {SHARD_DIR}")

workbooks = []
for shard_path in shard_paths:
    with shard_path.open(encoding="utf-8") as handle:
        workbooks.extend(json.load(handle)["files"])

with GRID_PATH.open(newline="", encoding="utf-8-sig") as handle:
    grid_by_id = {int(row["cell_id"]): row for row in csv.DictReader(handle)}

status_counts = Counter(workbook["status"] for workbook in workbooks)
observed_ids = {workbook["cellId"] for workbook in workbooks if workbook["status"] == "ok"}
missing_grid_ids = sorted(set(grid_by_id) - observed_ids)


# %% [markdown]
# ## Derive raw factors and availability

# %%
factor_rows = []
availability_rows = []
for scenario in SCENARIOS:
    for horizon in HORIZONS:
        valid = []
        missing_baseline = 0
        zero_baseline = 0
        missing_future = 0
        for workbook in workbooks:
            if workbook["status"] != "ok":
                continue
            totals = workbook["totals"].get(scenario, {})
            baseline = totals.get("2025")
            future = totals.get(horizon)
            if baseline is None:
                missing_baseline += 1
                continue
            if math.isclose(abs(baseline), 0.0, rel_tol=0.0, abs_tol=0.0):
                zero_baseline += 1
                continue
            if future is None:
                missing_future += 1
                continue
            factor = abs(future) / abs(baseline)
            valid.append(factor)
            grid_row = grid_by_id[workbook["cellId"]]
            factor_rows.append(
                {
                    "cell_id": workbook["cellId"],
                    "lat_center": float(grid_row["lat_center"]),
                    "lon_center": float(grid_row["lon_center"]),
                    "state_abbr": grid_row["state_abbr"],
                    "scenario": scenario,
                    "horizon": int(horizon),
                    "baseline_damage": baseline,
                    "future_damage": future,
                    "absolute_change_magnitude": abs(future) - abs(baseline),
                    "factor_raw": factor,
                }
            )
        availability_rows.append(
            {
                "scenario": scenario,
                "horizon": int(horizon),
                "source_workbooks": len(workbooks),
                "valid_factors": len(valid),
                "missing_baseline": missing_baseline,
                "zero_baseline": zero_baseline,
                "missing_future": missing_future,
                "missing_source_cells": len(missing_grid_ids),
            }
        )


# %% [markdown]
# ## Summarize the multiplier distribution

# %%
factors_by_slice = defaultdict(list)
for row in factor_rows:
    factors_by_slice[(row["scenario"], row["horizon"])].append(row["factor_raw"])

distribution_rows = []
for scenario in SCENARIOS:
    for horizon in map(int, HORIZONS):
        values = factors_by_slice[(scenario, horizon)]
        distribution_rows.append(
            {
                "scenario": scenario,
                "horizon": horizon,
                "years_from_2025": horizon - 2025,
                "n": len(values),
                "minimum": min(values) if values else None,
                "p01": quantile(values, 0.01),
                "p05": quantile(values, 0.05),
                "p10": quantile(values, 0.10),
                "p25": quantile(values, 0.25),
                "median": statistics.median(values) if values else None,
                "p75": quantile(values, 0.75),
                "p90": quantile(values, 0.90),
                "p95": quantile(values, 0.95),
                "p99": quantile(values, 0.99),
                "maximum": max(values) if values else None,
                "below_1x": sum(value < 1.0 - 1e-12 for value in values),
                "equal_1x": sum(math.isclose(value, 1.0, rel_tol=0.0, abs_tol=1e-12) for value in values),
                "above_1x": sum(value > 1.0 + 1e-12 for value in values),
                "above_1_1x": sum(value > 1.1 for value in values),
                "above_1_25x": sum(value > 1.25 for value in values),
                "above_1_5x": sum(value > 1.5 for value in values),
                "above_2x": sum(value > 2.0 for value in values),
            }
        )

baseline_distribution_rows = []
for scenario in SCENARIOS:
    values = [
        abs(workbook["totals"][scenario]["2025"])
        for workbook in workbooks
        if workbook["status"] == "ok" and workbook["totals"][scenario]["2025"] is not None
    ]
    baseline_distribution_rows.append(
        {
            "scenario": scenario,
            "n": len(values),
            "minimum": min(values),
            "p01": quantile(values, 0.01),
            "p05": quantile(values, 0.05),
            "p10": quantile(values, 0.10),
            "median": statistics.median(values),
            "p90": quantile(values, 0.90),
            "p95": quantile(values, 0.95),
            "p99": quantile(values, 0.99),
            "maximum": max(values),
            "below_1e_8": sum(value < 1e-8 for value in values),
            "below_1e_7": sum(value < 1e-7 for value in values),
            "below_1e_6": sum(value < 1e-6 for value in values),
            "below_1e_5": sum(value < 1e-5 for value in values),
            "below_1e_4": sum(value < 1e-4 for value in values),
        }
    )

selected_outliers = []
for scenario in SCENARIOS:
    for horizon in map(int, SELECTED_HORIZONS):
        rows = [
            row
            for row in factor_rows
            if row["scenario"] == scenario and row["horizon"] == horizon
        ]
        ordered = sorted(rows, key=lambda row: row["factor_raw"])
        for rank, row in enumerate(ordered[:20], start=1):
            selected_outliers.append({"tail": "lowest", "rank": rank, **row})
        for rank, row in enumerate(reversed(ordered[-20:]), start=1):
            selected_outliers.append({"tail": "highest", "rank": rank, **row})

baseline_floor_sensitivity = []
for scenario in SCENARIOS:
    for horizon in map(int, SELECTED_HORIZONS):
        selected = [
            row
            for row in factor_rows
            if row["scenario"] == scenario and row["horizon"] == horizon
        ]
        for floor in (0.0, 1e-8, 1e-7, 1e-6, 1e-5, 1e-4):
            values = [
                row["factor_raw"]
                for row in selected
                if abs(row["baseline_damage"]) >= floor
            ]
            baseline_floor_sensitivity.append(
                {
                    "scenario": scenario,
                    "horizon": horizon,
                    "baseline_floor": floor,
                    "retained": len(values),
                    "excluded": len(selected) - len(values),
                    "median": statistics.median(values),
                    "p90": quantile(values, 0.90),
                    "p99": quantile(values, 0.99),
                    "maximum": max(values),
                }
            )


# %% [markdown]
# ## Write compact evidence tables

# %%
def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=list(rows[0]),
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


write_csv(OUTPUT_DIR / "overall_delta_availability_by_horizon.csv", availability_rows)
write_csv(OUTPUT_DIR / "overall_delta_distribution_by_horizon.csv", distribution_rows)
write_csv(OUTPUT_DIR / "overall_delta_baseline_distribution.csv", baseline_distribution_rows)
write_csv(OUTPUT_DIR / "overall_delta_baseline_floor_sensitivity.csv", baseline_floor_sensitivity)
write_csv(OUTPUT_DIR / "overall_delta_selected_horizon_outliers.csv", selected_outliers)

summary = {
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "extracted_workbooks": len(workbooks),
    "parse_status_counts": status_counts,
    "canonical_cells": len(grid_by_id),
    "observed_canonical_cells": len(observed_ids),
    "missing_source_cells": len(missing_grid_ids),
    "scenarios": SCENARIOS,
    "horizons": HORIZONS,
    "selected_horizons": SELECTED_HORIZONS,
}
with (OUTPUT_DIR / "overall_delta_full_run_summary.json").open("w", encoding="utf-8") as handle:
    json.dump(summary, handle, indent=2)


# %% [markdown]
# ## Percentile-band view across horizons

# %%
fig, axes = plt.subplots(1, 2, figsize=(13, 4.8), sharey=True)
for axis, scenario in zip(axes, SCENARIOS):
    selected = [row for row in distribution_rows if row["scenario"] == scenario]
    years = [row["horizon"] for row in selected]
    axis.fill_between(years, [row["p01"] for row in selected], [row["p99"] for row in selected], alpha=0.16, label="P01–P99")
    axis.fill_between(years, [row["p10"] for row in selected], [row["p90"] for row in selected], alpha=0.28, label="P10–P90")
    axis.plot(years, [row["median"] for row in selected], linewidth=2.2, label="Median")
    axis.axhline(1.0, color="black", linewidth=0.8, linestyle="--")
    axis.set_title(scenario.upper())
    axis.set_xlabel("Horizon")
    axis.grid(alpha=0.2)
axes[0].set_ylabel("Raw overall damage multiplier (x)")
axes[0].legend(frameon=False)
fig.suptitle("SCR Solar overall physical-damage multiplier distribution")
fig.tight_layout()
fig.savefig(OUTPUT_DIR / "overall_delta_percentile_band.png", dpi=180, bbox_inches="tight")
plt.close(fig)


# %% [markdown]
# ## Selected-horizon spatial view

# %%
fig, axes = plt.subplots(2, 4, figsize=(16, 7.2), sharex=True, sharey=True)
for row_index, scenario in enumerate(SCENARIOS):
    for column_index, horizon in enumerate(map(int, SELECTED_HORIZONS)):
        axis = axes[row_index][column_index]
        selected = [
            row
            for row in factor_rows
            if row["scenario"] == scenario and row["horizon"] == horizon
        ]
        color_values = [max(-1.0, min(1.0, math.log2(row["factor_raw"]))) for row in selected]
        scatter = axis.scatter(
            [row["lon_center"] for row in selected],
            [row["lat_center"] for row in selected],
            c=color_values,
            cmap="coolwarm",
            vmin=-1.0,
            vmax=1.0,
            s=2.0,
            linewidths=0,
        )
        axis.set_title(f"{scenario.upper()} · {horizon}")
        axis.set_axis_off()
colorbar = fig.colorbar(scatter, ax=axes, orientation="horizontal", fraction=0.04, pad=0.04)
colorbar.set_ticks([-1, -0.585, 0, 0.585, 1])
colorbar.set_ticklabels(["0.50x", "0.67x", "1.00x", "1.50x", "2.00x+"])
colorbar.set_label("Raw multiplier (log₂ color scale; clipped for display)")
fig.suptitle("SCR Solar overall physical-damage multiplier across observed CONUS cells")
fig.savefig(OUTPUT_DIR / "overall_delta_selected_horizon_maps.png", dpi=180, bbox_inches="tight")
plt.close(fig)

summary

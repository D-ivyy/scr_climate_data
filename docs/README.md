# SCR Climate Data Export Notes

Status: script implemented and smoke-tested against the dev DB, 2026-06-30.

Operational guide: [`guide.md`](guide.md).

Script:

```bash
python scripts/export_scr_upload.py \
  --workspace-slug demo \
  --portfolio-name "Q3 Outlook"
```

## Purpose

SCR accepts a bulk-upload file, runs its climate / physical-risk
calculation, and returns an Excel workbook. The immediate InfraSure task is
to generate the SCR input file from the dev PostgreSQL database and preserve
a deterministic path back from the returned workbook to the database asset.

This is an identity bridge, not just a CSV writer.

## Required SCR Upload Fields

The meeting notes define the SCR bulk-upload input as:

- asset name
- address
- latitude
- longitude
- asset value

Client and portfolio names are intentionally excluded from the SCR upload.
Those are internal InfraSure mappings and should live in the private manifest
or database, not in the vendor-facing file.

## Template Mapping Confirmed

Template inspected:
`docs/Climate_Metrics_Import_tempate.xlsx`.

Primary upload sheet: `Assets`.

- Data rows start at row 10.
- Current template row capacity is 1,001 rows (`10:1010`). Split larger runs.
- Upload columns run from `B:BG`.
- Formula-backed columns:
  - `D` TICCS Class
  - `E` TICCS Class name
  - `F` NACE code
  - `G` Sector
  - `K` Country Code (ISO3)
- The script writes static lookup values into those columns for populated
  rows. This matches the known-working SCR workbook reviewed during
  development. Do not rely on SCR's backend to calculate Excel formulas.
- Template-marked mandatory fields by fill color:
  - `B` Asset Name
  - `C` Asset type
  - `I` Detention rate
  - `J` Country
  - `M:N` GPS coordinates
  - `O` Revenues
- Template-marked optional / proxy fields include `P` Asset Value and most
  strategy / resilience fields.
- `L` Address is marked optional / not used in modelling, but the exporter
  still fills a best-effort address because the meeting notes requested it.
- `H` Operating entity name is not mandatory and is intentionally blank by
  default. Use `--include-operating-entity` only when we intentionally want to
  send that optional information.

Important correction: the template treats `Revenues` as mandatory and
`Asset Value` as optional/proxy. That does not match the simplified meeting
note. The script records missing revenue as a warning by default and can reject
those rows with `--strict`.

## Database Identity Decision

Use the InfraSure UUID as the canonical join-back identity.

For plant-level rows:

- canonical DB key: `plants.id`
- SCR subject grain: `plant`
- optional metadata: `plants.slug`, `plants.eia_plant_id`,
  `plants.workspace_id`, `plants.source_type`

This works uniformly for both reference and tenant assets:

- reference asset: `plants.workspace_id IS NULL`, usually has
  `eia_plant_id`
- tenant / greenfield asset: `plants.workspace_id IS NOT NULL`, usually has
  `eia_plant_id IS NULL`

Do not build two identity systems for reference vs tenant assets. The UUID
already handles both.

## SCR Asset Name

SCR appears to treat `asset name` as the practical row identifier. InfraSure
should generate this value instead of using a raw display name.

Preferred SCR-compatible stable form:

```text
is_p_<plant_uuid_without_dashes>
```

This keeps the upload asset name to 37 characters, close to the known-working
file's observed asset-name length range. The slug/display name stays in the
internal manifest.

If we later confirm SCR accepts longer names, the exporter can still emit:

```text
<plant_slug>__is_p_<plant_uuid_without_dashes>
```

For future generator-level rows:

```text
is_g_<generator_uuid_without_dashes>
```

or, if longer names are confirmed safe:

```text
<plant_slug>__is_g_<generator_uuid_without_dashes>
```

The UUID suffix is the real identity. If SCR returns only the `asset name`,
the UUID embedded in that string plus the private manifest is enough to map
the output back.

## SCR Returned Output Examples

Example SCR result files are kept in
`docs/output_examples/`:

- `asset_1232_physical_risks.xlsx`
- `asset_1232_transition_risks.xlsx`

Both workbooks preserve our generated `assetName` exactly, for example:

```text
is_p_f0d551408183414598a0bd83bf10ee72
```

That confirms the intended join-back contract:

```text
SCR Output.assetName -> scr_manifest.csv.scr_asset_name -> plants.id
```

SCR's `assetId` should be stored as vendor metadata, not as the InfraSure
database key. See [`guide.md`](guide.md) for the physical and transition
output schemas and the proposed ingestion plan.

## Files Per Run

Each SCR export run produces these artifacts:

1. `scr_upload.xlsx`
   - Slim one-sheet workbook containing only the `Assets` sheet.
   - Writes static values for TICCS/NACE/country-code columns in populated
     rows so server-side parsers do not need to calculate formulas.

2. `scr_upload_template.xlsx`
   - Full template-shaped fallback with support sheets retained.
   - Also writes static values in populated rows.

3. `scr_upload.csv`
   - Vendor-facing CSV with single-line headers.
   - Computes the formula-derived fields directly, because CSV cannot carry
     Excel formulas.

4. `scr_manifest.csv`
   - Internal-only mapping file.
   - Must not be uploaded unless SCR explicitly supports hidden metadata.

5. `scr_rejects.csv`
   - Rows selected from the DB but not written to the upload file because
     they are missing core fields such as latitude or longitude.

6. `run_manifest.json`
   - Run-level metadata and warning/error counts.

The manifest contains:

- `scr_run_id`
- `scr_asset_name`
- `scr_grain` (`plant` for v1)
- `plant_uuid`
- `generator_uuid` (null for v1 plant rows)
- `plant_slug`
- `eia_plant_id`
- `eia_generator_code` (null for v1 plant rows)
- `workspace_id`
- `portfolio_id`
- `source_type`
- `asset_value`
- `asset_value_source`
- row-level validation status / missing-field notes

## Script Selection Modes

Supported selection modes:

```bash
# Portfolio export, the normal path
.../export_scr_upload.py --workspace-slug demo --portfolio-name "Q3 Outlook"

# Workspace export, defaults to workspace_asset.state='portfolio'
.../export_scr_upload.py --workspace-slug demo

# Include prospect-state workspace assets too
.../export_scr_upload.py --workspace-slug demo --asset-state all

# Specific plant UUID(s)
.../export_scr_upload.py --plant-uuid <plants.id> --plant-uuid <plants.id>

# Test-only broad reference export
.../export_scr_upload.py --all-reference --limit 100
```

Default target is the dev DB (`DATABASE_URL_DEV` from `.env`, unless
`--env-file` or `--database-url` is provided). Production requires
`--target prod` explicitly.

## Sidecar Inputs

Use `--asset-values <csv>` for fields that are not canonical in the DB yet.
Rows can be keyed by any of:

- `plant_uuid`
- `scr_asset_name`
- `portfolio_asset_id`
- `eia_plant_id`

Recognized sidecar columns include:

- `asset_value` or `asset_value_usd`
- `revenues` or `annual_revenue_usd`
- `year` or `valuation_year`
- `detention_rate`
- `operating_entity_name` only when `--include-operating-entity` is used
- `address`
- `asset_type`
- `scope_1`, `scope_2`

Resilience and strategy columns can also be passed with snake_case names that
match the script's output keys, for example
`flood_blue_green_infrastructure`.

Later, the manifest can become a proper database table. For v0, a run folder
is enough.

## Coordinate Grain Confirmation

Current InfraSure dev DB and EIA pipeline should be treated as plant-level
for SCR coordinates.

Confirmed on 2026-06-30 from the derived dev DB:

- `plants` stores the canonical asset row and `plants.data` carries plant
  `lat/lon` or `latitude/longitude` values.
- `generators` has no coordinate columns.
- `engineering_subsystem` and `engineering_component` have no coordinate
  columns.

Confirmed on 2026-06-30 from the raw EIA source files used by the pipeline:

- `data/sources/eia/eia860m/april_generator2026.xlsx`
  - This is the exact EIA-860M workbook recorded in
    `data/base/manifest.json` as the source for `asset_master.parquet`.
  - The base loader reads exactly the `Operating` and `Planned` sheets and
    concatenates them.
  - Both sheets include `Latitude` and `Longitude` on generator-inventory
    rows.
  - Within the raw sheets, the coordinate values are repeated for every
    generator under the same `Plant ID`.
  - Raw sheet check:
    - `Operating`: 27,973 rows, 14,348 plants, 4,712 multi-generator plants,
      0 multi-generator plants with multiple lat/lon pairs.
    - `Planned`: 2,258 rows, 1,500 plants, 324 multi-generator plants,
      0 multi-generator plants with multiple lat/lon pairs.
    - Combined build input (`Operating` + `Planned`): 30,225 rows, 15,749
      plants, 5,032 multi-generator plants, 0 multi-generator plants with
      multiple lat/lon pairs and 0 multi-generator plants with partially
      missing lat/lon rows.
  - The generated `data/base/asset_master.parquet` has the same result:
    30,225 rows, 15,749 plants, 5,032 multi-generator plants, and 0
    multi-generator plants with multiple lat/lon pairs.
- `data/sources/eia/eia8602024/2___Plant_Y2024.xlsx`
  - The `Plant` schedule has `Latitude` and `Longitude` columns at the plant
    schedule grain.
- `data/sources/eia/eia8602024/3_1_Generator_Y2024.xlsx`
  - The `Operable` and `Proposed` generator schedules have no coordinate
    columns.

The base schema records this as `Latitude` / `Longitude` from `860M` with
description `Plant latitude` / `Plant longitude`, and the export path maps
these values into plant-level `lat/lon`.

There are more granular coordinates in some auxiliary sources, such as
USWTDB turbine locations for wind, and OSM-derived boundary / centroid data.
Those are useful future inputs, but they are not a universal
generator-level coordinate model in the current platform schema.

## Live Dev DB Check

Read-only check on 2026-06-30 against the dev DB:

- `plants`: 15,755 rows total
- reference plants: 15,749
- tenant / user-added plants: 6
- `workspace_asset`: 151 rows
- active `portfolio_asset`: 129 rows
- reference plants missing `plant_index` coordinates: 0
- active portfolio rows missing coordinates: 2
- tenant / user-added plants with non-empty lat/lon in `plants.data`: 1 of 6

The two active portfolio rows currently rejected by the script are tenant
assets in the `demo` workspace / `Q3 Outlook` portfolio:

- `hybrid-test-ak-3f1823`
- `test-az-1dbc35`

Both have `latitude` / `longitude` keys in JSON but blank values. This is why
the script writes them to `scr_rejects.csv` and does not put them in the SCR
upload file.

## V1 Grain Decision

Version 1 should export one SCR row per plant / site.

Rationale:

- SCR's required fields are site-like: name, address, latitude, longitude,
  asset value.
- The workspace relationship layer is plant-grain:
  `workspace_asset(workspace_id, plant_id)`.
- `portfolio_asset.reference_plant_id` points to `plants.id`.
- Current coordinates are plant-level, not generator-level.

Generator-level export remains a future option for hybrid or physically split
assets, but it should wait until we have reliable generator-level coordinates
or an explicit split instruction from the user.

## Hybrid Assets

Hybrid assets are the main reason to keep the future generator-level concept
alive. A plant can contain multiple generators with different technologies,
and some real-world "plants" may represent assets that are physically spread
across a site.

For v1, do not split hybrids automatically. Export the parent plant as one
SCR row. If a user needs a hybrid split before the schema supports
generator-level coordinates, require an explicit override / selection file
that supplies the per-subject latitude, longitude, address, and asset value.

## Asset Value

`asset value` is the least settled required field. It is not currently a
simple canonical flat column on `plants` or `plant_index`.

Recommended v0 rule:

- require a sidecar asset-value input keyed by `plant_uuid` or generated
  `scr_asset_name`; or
- require the value to already exist in a tenant/private field once that
  storage decision is made.

The script follows that rule:

- default `--asset-value-source sidecar`: leaves missing asset value blank and
  records `missing_asset_value` in the manifest warnings.
- explicit `--asset-value-source capex_proxy`: derives
  `latest_capex_per_kw * total_capacity_mw * 1000` when both fields exist and
  records `capex_proxy_latest_capex_per_kw_times_mw_times_1000`.

Do not treat the capex proxy as a true asset valuation.

## Revenues

The template marks `Revenues` as mandatory, but the current DB does not expose
a clean plant-level annual revenue value for this purpose.

Recommended v0 rule:

- provide `revenues` through the sidecar; or
- run without `--strict` and accept that missing revenue is recorded as a
  warning and left blank in the upload.

Use `--strict` when preparing an upload that should fail closed on missing
template-mandatory financial fields.

Use `--require-asset-value` for actual SCR uploads unless SCR confirms asset
value can be blank.

## SCR 500 Troubleshooting Finding

Compared against the known-working workbook
reviewed during development after an SCR 500:

- The working file stores `TICCS Class`, `TICCS Class name`, `NACE code`,
  `Sector`, and `Country Code` as static text values in populated rows.
- Our earlier generated Excel stored formulas in those cells with no cached
  values. `data_only=True` reads those cells as blank.
- A server-side parser that does not recalculate Excel formulas can therefore
  see missing lookup fields and fail.
- The exporter now writes static lookup values into populated rows.
- The working file also uses short asset names. The exporter now defaults to
  compact UUID-only asset names (`is_p_<uuid_without_dashes>`) while retaining
  all human-readable context in `scr_manifest.csv`.
- `scr_upload.xlsx` is now a slim one-sheet workbook. Use
  `scr_upload_template.xlsx` only if SCR requires the full workbook shape.

## File Size Strategy

SCR reportedly has an upload limit around 20 MB.

- Prefer `scr_upload.csv` if SCR accepts CSV. It has direct values and no
  workbook support sheets.
- If XLSX is required, prefer `scr_upload.xlsx`, which contains only `Assets`.
  This compact workbook path has been tested by the user and works with SCR
  as of 2026-07-01.
- Keep `scr_upload_template.xlsx` as a fallback if SCR expects the full
  original workbook structure.

`runs/` contains generated artifacts. Stale run directories can be deleted
after preserving any returned SCR output and the matching `scr_manifest.csv`
needed for join-back.

## Operating Entity Policy

Initial uploads should omit operating entities.

The template does not mark `Operating entity name` as mandatory, and we do not
need to disclose that information for the first SCR file-validation pass. The
script therefore leaves column `H` blank by default. Passing
`--include-operating-entity` is an explicit opt-in.

## Remaining Questions

- Does SCR accept underscores, UUIDs, and long asset-name strings?
- What is the source of truth for `asset value` in v0?
- What is the source of truth for `revenues` in v0?
- Is county/state acceptable in `Address` when street address is missing?
- What final database table names should we use for normalized SCR physical
  and transition outputs after local import review?

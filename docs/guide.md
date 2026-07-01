# SCR Climate Data Export Guide

Status: v0 guide for the dev-DB exporter, 2026-06-30.

This guide explains what the SCR exporter writes, which files are safe to
upload, and how to interpret accepted rows, warnings, and rejects.

## Mental Model

The exporter has two jobs:

1. Build a vendor-facing SCR upload file.
2. Preserve a private join-back map from SCR rows to InfraSure database
   assets.

Those are deliberately separate. SCR should receive only the upload file.
InfraSure keeps the manifest and rejects files internally.

## Main Command

Run from this repo after installing `requirements.txt` and creating `.env`:

```bash
python scripts/export_scr_upload.py \
  --workspace-slug demo \
  --portfolio-name "Q3 Outlook"
```

Default behavior:

- targets the dev DB (`DATABASE_URL_DEV` from `.env`, unless `--env-file` or
  `--database-url` is provided)
- exports plant-level rows
- writes to `runs/<run_id>/`
- uses compact UUID-only SCR asset names by default
- omits optional operating-entity names from the upload
- writes rows with missing latitude/longitude to `scr_rejects.csv`
- leaves missing revenue / asset value blank unless provided by sidecar

## Common Runs

Portfolio export, normal path:

```bash
.../export_scr_upload.py \
  --workspace-slug demo \
  --portfolio-name "Q3 Outlook"
```

Small smoke test:

```bash
.../export_scr_upload.py \
  --workspace-slug aig_client_portfolio \
  --portfolio-name "AIG Client Portfolio" \
  --limit 5 \
  --run-id test_aig_5
```

Export one or more known plants:

```bash
.../export_scr_upload.py \
  --plant-uuid <plants.id> \
  --plant-uuid <plants.id>
```

Use a sidecar for asset value and revenue:

```bash
.../export_scr_upload.py \
  --workspace-slug demo \
  --portfolio-name "Q3 Outlook" \
  --asset-values /path/to/scr_asset_values.csv
```

Require asset value for actual upload runs:

```bash
.../export_scr_upload.py \
  --workspace-slug demo \
  --portfolio-name "Q3 Outlook" \
  --asset-values /path/to/scr_asset_values.csv \
  --require-asset-value
```

Fail closed on missing template-mandatory financial fields:

```bash
.../export_scr_upload.py \
  --workspace-slug demo \
  --portfolio-name "Q3 Outlook" \
  --asset-values /path/to/scr_asset_values.csv \
  --strict
```

Populate optional operating entities only when intentionally needed:

```bash
.../export_scr_upload.py \
  --workspace-slug demo \
  --portfolio-name "Q3 Outlook" \
  --include-operating-entity
```

## Output Folder

Each run writes:

```text
scr_upload.xlsx
scr_upload_template.xlsx
scr_upload.csv
scr_manifest.csv
scr_rejects.csv
run_manifest.json
```

Only `scr_upload.csv`, `scr_upload.xlsx`, or `scr_upload_template.xlsx` should
be uploaded to SCR. The manifest/reject/run files are internal.

## File Purposes

| File | Upload to SCR? | Row set | Purpose |
|---|---:|---|---|
| `scr_upload.csv` | Yes, preferred if SCR accepts CSV | Accepted rows only | Smallest upload. Direct values only; no formulas or reference sheets. |
| `scr_upload.xlsx` | Yes | Accepted rows only | Slim one-sheet workbook containing only `Assets`. Direct values only. |
| `scr_upload_template.xlsx` | Yes, fallback | Accepted rows only | Full template-shaped workbook with support sheets retained. Direct values in populated rows. |
| `scr_manifest.csv` | No | All selected rows | Internal join-back map and validation audit. |
| `scr_rejects.csv` | No | Rejected rows only | Fix list for selected assets that could not safely be sent to SCR. |
| `run_manifest.json` | No | Run summary | Counts, options, DB target, warnings, errors. |

## Upload Schema

The template upload sheet is `Assets`.

- Data begins at row 10.
- The template currently supports rows 10 through 1010.
- `scr_upload.csv` flattens the same data into single-line headers.
- `scr_upload.xlsx` keeps only the `Assets` sheet to minimize file size.
- `scr_upload_template.xlsx` keeps the original template support sheets for
  fallback testing if SCR requires workbook context.

Upload fields:

| CSV header | Excel column | Filled by exporter? | Notes |
|---|---:|---:|---|
| `Asset Name` | B | Yes | Generated traceable ID: `is_p_<uuid_without_dashes>` by default. |
| `Asset type` | C | Yes | Inferred from fuel/technology or sidecar override. |
| `TICCS Class` | D | Yes | Static lookup value in populated `.xlsx` rows; precomputed in `.csv`. |
| `TICCS Class name` | E | Yes | Static lookup value. |
| `NACE code` | F | Yes | Static lookup value. |
| `Sector` | G | Yes | Static lookup value. |
| `Operating entity name` | H | Blank by default | Optional; only filled with `--include-operating-entity`. |
| `Detention rate` | I | Optional today | Blank by default; override with sidecar or `--detention-rate`. |
| `Country` | J | Yes | Defaults to `United States`. |
| `Country Code (ISO3)` | K | Yes | Static lookup value, normally `USA`. |
| `Address` | L | Best effort | Uses sidecar, DB address, city/state, county/state, or state fallback. |
| `Latitude` | M | Required | Rejects row if missing. |
| `Longitude` | N | Required | Rejects row if missing. |
| `Revenues` | O | Sidecar only today | Template-marked mandatory; warning if missing, reject with `--strict`. |
| `Asset Value` | P | Sidecar or explicit proxy | Optional/proxy in template; warning if missing. |
| `Year` | Q | Yes | Defaults to current script year; override with sidecar or `--valuation-year`. |
| `Scope 1` / `Scope 2` | R:S | Optional sidecar | Blank unless sidecar provides values. |
| Decarbonisation fields | T:U | Optional sidecar | Valid values should be 0 to 1. |
| Flood / storm / heat / wildfire fields | V:BG | Optional sidecar | Valid values should be 0 to 1. |

## Operating-Entity Policy

Initial SCR exports should not include operating entities.

Reasoning:

- The template does not mark `Operating entity name` as mandatory.
- SCR can test location and asset-type processing without it.
- It exposes extra internal/contextual information that is not needed for the
  initial upload.

The exporter therefore leaves column `H` blank by default. Use
`--include-operating-entity` only when there is a specific reason to send it.

## SCR 500 Troubleshooting

The known-working file from Downloads was compared against an earlier generated
file after SCR returned a 500.

Most important finding:

- Working file: populated rows have static values in `D/E/F/G/K`.
- Earlier generated file: populated rows had formulas in `D/E/F/G/K` and no
  cached formula values.
- Many server-side Excel parsers do not recalculate formulas. They read those
  cells as blank.

The exporter now writes static lookup values for populated rows.

Other compatibility changes:

- Asset names default to `is_p_<uuid_without_dashes>`, 37 characters.
- Detention rate is blank by default because the working file had it blank.
- Use `--require-asset-value` for upload runs, because the working file had
  asset value populated for every uploaded row.
- `scr_upload.xlsx` is now a slim one-sheet workbook. Use
  `scr_upload_template.xlsx` only if SCR rejects the one-sheet version because
  it expects the full workbook shape.

## File Size Strategy

SCR reportedly has an upload limit around 20 MB.

Recommended order:

1. Try `scr_upload.csv` if SCR accepts CSV. It has direct values and no extra
   sheets, so it scales best.
2. If SCR requires XLSX, try `scr_upload.xlsx`. It has only the `Assets` sheet.
3. If SCR requires the original template workbook structure, use
   `scr_upload_template.xlsx` as a fallback.

The reference sheets are useful while building the file, but they are not
needed once lookup values are written directly into the upload sheet.

## Confirmed Working Path

As of 2026-07-01, the compact one-sheet workbook path has been tested by the
user and works with SCR.

Use this as the default upload target:

```text
runs/<run_id>/scr_upload.xlsx
```

Keep `scr_upload_template.xlsx` only as a fallback if SCR changes behavior and
starts requiring the original multi-sheet workbook shape.

The `runs/` folder is generated output. It is safe to delete stale run
directories after keeping any returned SCR output and the matching
`scr_manifest.csv` needed for join-back.

## Public Repo Note

The SCR template workbook, returned SCR output workbooks, generated uploads,
manifests, and `.env` files are local-only artifacts and are ignored by git in
this public repository.

Expected local paths when working with the current defaults:

```text
.env
docs/Climate_Metrics_Import_tempate.xlsx
docs/output_examples/*.xlsx
runs/<run_id>/*
```

## Manifest Schema

`scr_manifest.csv` is internal. It exists because SCR output must be mapped
back to the database after SCR returns its results.

It includes all selected rows, not just upload rows.

Columns:

```text
scr_run_id
generated_at
scr_asset_name
scr_grain
plant_uuid
generator_uuid
plant_slug
eia_plant_id
eia_generator_code
workspace_id
workspace_slug
portfolio_id
portfolio_name
portfolio_asset_id
workspace_asset_state
source_type
plant_name
asset_type
address
address_source
latitude
longitude
detention_rate
revenues
revenue_source
asset_value
asset_value_source
valuation_year
primary_fuel
fuel_types
technologies
total_capacity_mw
latest_capex_per_kw
validation_status
validation_errors
validation_warnings
```

Important columns:

| Column | Meaning |
|---|---|
| `scr_asset_name` | The row identifier SCR will return. Contains the plant UUID suffix. |
| `plant_uuid` | Canonical InfraSure `plants.id`; works for reference and tenant assets. |
| `portfolio_asset_id` | Internal portfolio membership row, when selected through a portfolio. |
| `validation_status` | `accepted` or `rejected`. |
| `validation_errors` | Hard blockers that kept a row out of upload. |
| `validation_warnings` | Non-blocking issues, usually blank financial fields or proxy use. |
| `asset_value_source` | `sidecar`, `missing`, or explicit proxy formula. |
| `address_source` | Shows whether address came from sidecar, DB field, or fallback. |

## Rejects Schema

`scr_rejects.csv` has the same columns as `scr_manifest.csv`, but contains
only rows where `validation_status = rejected`.

A reject means: the asset was selected from the DB, but the script did not put
it in `scr_upload.xlsx` or `scr_upload.csv`.

Current hard reject reasons:

| Error | Meaning | Fix |
|---|---|---|
| `missing_latitude` | No usable latitude in DB or sidecar. | Add/fix latitude before upload. |
| `missing_longitude` | No usable longitude in DB or sidecar. | Add/fix longitude before upload. |
| `asset_type_not_in_template:<value>` | Asset type not present in SCR template list. | Correct mapping or sidecar asset type. |
| `missing_revenues_strict` | `--strict` was used and revenue is blank. | Add revenue sidecar. |
| `missing_asset_value_strict` | `--strict` was used and asset value is blank. | Add asset value sidecar. |

For example, in `test_demo_q3`, 25 assets were selected, 23 were accepted, and
2 were rejected because tenant-added assets had blank latitude and longitude.

## Run Manifest

`run_manifest.json` is the run-level summary.

Useful fields:

| Field | Meaning |
|---|---|
| `scr_run_id` | Folder/run identifier. |
| `target` | `dev` or `prod`; default is `dev`. |
| `db_host` | DB host without credentials; confirms the branch used. |
| `workspace_slug` / `portfolio_name` | Selection inputs. |
| `selected_rows` | Rows pulled from the DB. |
| `accepted_rows` | Rows written to upload files. |
| `rejected_rows` | Rows written only to rejects. |
| `rows_with_warnings` | Accepted or rejected rows with non-blocking warnings. |
| `warning_counts` | Aggregated warning types. |
| `error_counts` | Aggregated hard reject types. |
| `include_operating_entity` | Whether optional operating entities were sent. |

Sanity check:

```text
selected_rows = accepted_rows + rejected_rows
```

## Sidecar Schema

Use a sidecar CSV when values do not live cleanly in the DB yet.

The sidecar can be keyed by any of:

```text
plant_uuid
scr_asset_name
portfolio_asset_id
eia_plant_id
```

Common sidecar columns:

```text
plant_uuid,asset_value,revenues,year,address,detention_rate,asset_type
```

Example:

```csv
plant_uuid,asset_value,revenues,year,address
801ffb04-5518-4ad1-a39e-d6ecc2ff75ba,379045396,48000000,2026,"Woodford County, IL, USA"
```

Sidecar values override DB-derived/default values for their row.

## Asset Value

The current DB does not expose a clean plant-level valuation field for SCR.

Recommended upload path:

```bash
.../export_scr_upload.py \
  --workspace-slug demo \
  --portfolio-name "Q3 Outlook" \
  --asset-values /path/to/asset_values.csv
```

Testing-only path:

```bash
.../export_scr_upload.py \
  --workspace-slug demo \
  --portfolio-name "Q3 Outlook" \
  --asset-value-source capex_proxy
```

The proxy formula is:

```text
latest_capex_per_kw * total_capacity_mw * 1000
```

Do not treat the proxy as a true asset valuation.

## Interpretation Checklist

Before sending a file to SCR:

1. Open `run_manifest.json`.
2. Confirm `target = dev` and the DB host is the expected dev host.
3. Confirm `rejected_rows = 0`, or intentionally accept that rejected rows are
   excluded.
4. Confirm `include_operating_entity = false` for initial uploads.
5. Review `warning_counts`.
6. If warnings include missing revenue or missing asset value, decide whether
   the test is still valid.
7. Upload only `scr_upload.xlsx` or `scr_upload.csv`.
8. Keep `scr_manifest.csv` with the SCR returned workbook for join-back.

## Join-Back After SCR Returns Results

SCR returned-output examples live in:

```text
docs/output_examples/asset_1232_physical_risks.xlsx
docs/output_examples/asset_1232_transition_risks.xlsx
```

Detailed returned-output schema and usage notes:
[`output_examples/schema.md`](output_examples/schema.md).

Both examples have the same workbook shape:

- `ReadMe`: asset metadata and field definitions
- `Output`: long-format result rows

The important finding is that SCR preserved the upload `assetName` exactly:

```text
is_p_<plant_uuid_without_dashes>
```

That makes the output join-back path deterministic:

```text
SCR Output.assetName
  -> scr_manifest.csv.scr_asset_name
  -> scr_manifest.csv.plant_uuid
  -> plants.id
```

Use `assetName` from the `Output` sheet as the primary row-level join key.
The `ReadMe` sheet is useful for a quick single-asset check, but ingestion
should not depend on `ReadMe` being one asset forever.

Do not join SCR results back by plant display name, address, coordinates,
country, TICCS class, or SCR's `assetId`.

`assetId` appears to be SCR's internal/external asset identifier. In the
examples it is `USA_00490`. Store it for audit and reconciliation, but do
not treat it as the InfraSure database key.

If the matching `scr_manifest.csv` is unavailable, the UUID can be recovered
from `assetName` for plant-level rows:

```text
assetName = is_p_f0d551408183414598a0bd83bf10ee72
plant_uuid = f0d55140-8183-4145-98a0-bd83bf10ee72
```

That fallback can recover the database asset, but it loses run context such
as `scr_run_id`, `portfolio_asset_id`, workspace, portfolio, asset value
source, and validation warnings. Keep the manifest beside every returned SCR
workbook.

## SCR Physical Risk Output

Example:

```text
docs/output_examples/asset_1232_physical_risks.xlsx
```

Observed shape:

- `ReadMe`: 51 rows, 106 columns
- `Output`: 953 rows, 36 columns
- one header row plus 952 data rows for the example asset
- no formulas observed in the returned workbook XML
- `ReadMe.assetName` and every `Output.assetName` value match the uploaded
  generated name

The physical `Output` sheet is long-format. The grain is approximately:

```text
assetName + scenario + timeHorizon + indicator + hazard
```

Columns:

```text
assetId
assetName
reportDate
geolocationCoordinates
countryCode
climateZone
ticcsSubClass
ticcsSubClassName
scenario
timeHorizon
indicator
indicatorUnit
indicatorValue
indicatorRating
hazard
HazardRating
hazardDamage
adjustedHazardDamage
hazardDisruption
adjustedHazardDisruption
hazardDisruptionDamageEquivalent
adjustedHazardDisruptionDamageEquivalent
hazardValueImpact
adjustedHazardValueImpact
hazardExposureRating
adjustedHazardExposureRating
totalDamage
adjustedTotalDamage
totalDisruption
adjustedTotalDisruption
totalDisruptionDamageEquivalent
adjustedTotalDisruptionDamageEquivalent
totalValueImpact
adjustedTotalValueImpact
physicalExposureRating
adjustedPhysicalExposureRating
```

Interpretation notes:

- `scenario` uses SSP-style scenario names in the physical output, for
  example `ssp2-4.5`.
- `timeHorizon` can include `Historical` plus future horizons.
- `indicator` / `indicatorValue` describe the climate indicator, for example
  water stress.
- `hazard` groups the risk driver, for example drought.
- The damage, disruption, equivalent, and value-impact fields are model
  outputs. Keep them as numeric values in the raw ingestion layer; apply any
  percent display conversion only in downstream presentation.
- Rating fields are categorical SCR ratings and should be stored as text.

## SCR Transition Risk Output

Example:

```text
docs/output_examples/asset_1232_transition_risks.xlsx
```

Observed shape:

- `ReadMe`: 36 rows, 106 columns
- `Output`: 241 rows, 20 columns
- one header row plus 240 data rows for the example asset
- no formulas observed in the returned workbook XML
- `ReadMe.assetName` and every `Output.assetName` value match the uploaded
  generated name

The transition `Output` sheet is long-format. The grain is approximately:

```text
assetName + scenario + timeHorizon + indicator + subrisk
```

Columns:

```text
assetId
assetName
reportDate
geolocationCoordinates
countryCode
climateZone
ticcsSubClass
ticcsSubClassName
scenario
timeHorizon
indicator
indicatorUnit
indicatorValue
subrisk
subriskRevenueImpact
adjustedSubriskRevenueImpact
subriskExposureRating
adjustedSubriskExposureRating
transitionExposureRating
adjustedTransitionExposureRating
```

Interpretation notes:

- `scenario` uses transition/economic scenario names, for example
  `Below 2°C`.
- `timeHorizon` is year-based in the example.
- `subrisk` identifies the transition risk driver, for example direct carbon
  cost or market demand shifts.
- Revenue-impact fields are model outputs. Store them as numeric values and
  decide display scaling later.
- Rating fields are categorical SCR ratings and should be stored as text.

## SCR Output Ingestion Plan

No database write-back script exists yet. The v1 ingestion script should do
this:

1. Accept one or more SCR result workbooks plus the matching
   `scr_manifest.csv`.
2. Detect physical vs transition output by required columns:
   `hazard` for physical, `subrisk` for transition.
3. Read the `Output` sheet only for row-level results.
4. Join `Output.assetName` to `scr_manifest.csv.scr_asset_name`.
5. Validate that the UUID suffix in `assetName` matches
   `scr_manifest.csv.plant_uuid`.
6. Preserve SCR `assetId` as vendor metadata.
7. Write normalized local outputs first, before any DB write:
   `scr_physical_risk_long.csv` and `scr_transition_risk_long.csv`.
8. Only after review, promote those normalized outputs into database tables.

Recommended normalized physical key:

```text
scr_run_id
plant_uuid
portfolio_asset_id
scr_asset_id
scr_asset_name
report_date
scenario
time_horizon
indicator
hazard
```

Recommended normalized transition key:

```text
scr_run_id
plant_uuid
portfolio_asset_id
scr_asset_id
scr_asset_name
report_date
scenario
time_horizon
indicator
subrisk
```

Keep raw SCR column names in the first normalized files. Rename to internal
snake_case only when creating database tables, so the first import remains
easy to reconcile against the vendor workbook.

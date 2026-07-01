# SCR Output Examples

Local returned examples from SCR define the current inbound result shape:

```text
asset_1232_physical_risks.xlsx
asset_1232_transition_risks.xlsx
```

The `.xlsx` files themselves are intentionally local-only and ignored by git
because this repository is public. Keep returned SCR workbooks outside version
control and use this folder for local analysis.

Both workbooks contain:

- `ReadMe`: asset metadata and field definitions
- `Output`: row-level result data
- Static values only; no formulas were found in the worksheet XML.

The key finding is that SCR returns the uploaded `assetName` unchanged. That
means we can connect SCR results back to InfraSure through the private
manifest from the matching upload run:

```text
Output.assetName -> scr_manifest.csv.scr_asset_name -> plant_uuid -> plants.id
```

`assetId` is SCR's returned identifier, for example `USA_00490`. Keep it as
vendor metadata, but do not use it as the InfraSure database key.

## Files

`asset_1232_physical_risks.xlsx`:

- `Output` has 36 columns.
- Observed data rows: 952.
- Row grain is roughly `assetName + scenario + timeHorizon + indicator +
  hazard`.
- Includes physical risk values such as damage, disruption,
  disruption-damage equivalent, value impact, total impact, and exposure
  ratings.

`asset_1232_transition_risks.xlsx`:

- `Output` has 20 columns.
- Observed data rows: 240.
- Row grain is roughly `assetName + scenario + timeHorizon + indicator +
  subrisk`.
- Includes transition risk values such as subrisk revenue impact and exposure
  ratings.

The full join-back and ingestion notes are in
[`../guide.md`](../guide.md).

The detailed returned-output schema and product/database usage notes are in
[`schema.md`](schema.md).

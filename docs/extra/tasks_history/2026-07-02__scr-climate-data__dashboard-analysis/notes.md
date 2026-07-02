# Notes: SCR Climate Data Dashboard and Output Analysis

## Repository And Run Context

Working repo:

```text
/Users/divy/code/personal/renewablesinfo/scr_climate_data
```

Platform symlink/location used during the work:

```text
/Users/divy/code/personal/renewablesinfo_org/.lab/scr_climate_data
```

GitHub remote:

```text
git@github.com:D-ivyy/scr_climate_data.git
```

Latest relevant commits:

```text
b380c84 Add hazard magnitude response plots
d0f278d Add hazard curve details
3d2a7ca Add physical disruption trend toggle
9f87341 Improve SCR hazard detail UX
9d48853 Add SCR dashboard context controls
f2aaa05 Improve SCR dashboard metric presentation
c295f16 Add local SCR dashboard
```

## Key Data Facts

Example returned files:

```text
docs/output_examples/asset_1232_physical_risks.xlsx
docs/output_examples/asset_1232_transition_risks.xlsx
```

Observed shapes:

```text
Physical rows:   952
Transition rows: 240
Assets:          1
```

Sample asset:

```text
assetName = is_p_f0d551408183414598a0bd83bf10ee72
assetId   = USA_00490
TICCS     = IC101020 / Gas-Fired Power Generation
Location  = (47.079722,-122.365)
Country   = USA
Zone      = Temperate
```

Transition subrisks:

```text
Direct_carbon_cost
Market_demand_shifts
```

Transition indicators:

```text
Direct_carbon_cost:
  - Carbon price
  - scope12_intensity

Market_demand_shifts:
  - Inflation
  - Revenue growth
  - scope3_intensity
```

## Physical Metrics Used

Dashboard physical trend toggle:

```text
Value       -> adjustedTotalValueImpact
Disruption  -> adjustedTotalDisruption
```

Hazard dropdown returned curves:

```text
adjustedHazardDamage
adjustedHazardDisruption
adjustedHazardDisruptionDamageEquivalent
adjustedHazardValueImpact
```

Relationship confirmed in sample for Flood/Wildfire:

```text
adjustedHazardValueImpact
  = adjustedHazardDamage
  + adjustedHazardDisruptionDamageEquivalent
```

Example, `ssp5-8.5 @ 2100`:

```text
Flood:
  adjustedHazardDamage                       0.0007529177105248538
  adjustedHazardDisruption                   0.0007426037692847874
  adjustedHazardDisruptionDamageEquivalent   0.0001441949066572403
  adjustedHazardValueImpact                  0.0008971126171820941

Wildfire:
  adjustedHazardDamage                       0.00006170536901697116
  adjustedHazardDisruption                   0.00006086008998934144
  adjustedHazardDisruptionDamageEquivalent   0.00001181749320181387
  adjustedHazardValueImpact                  0.00007352286221878504

Heat:
  adjustedHazardDamage                       null
  adjustedHazardDisruption                   0.001381653372387103
  adjustedHazardDisruptionDamageEquivalent   0.0002682822082305054
  adjustedHazardValueImpact                  null
```

## Magnitude-Response Caveat

The dashboard now includes a derived magnitude-response section:

```text
x = returned indicatorValue
y = selected returned hazard metric
```

This is not an official SCR damage function. The raw workbook gives row-level indicator magnitudes and repeated hazard-level metrics. It does not explicitly provide a vendor vulnerability curve. The dashboard labels this section as derived.

Examples:

- Wildfire under `ssp5-8.5` can show `Fire Weather Index (FWI)` versus `adjustedHazardDamage`.
- Heat under `ssp5-8.5` can show `Heatwave days` versus `adjustedHazardDisruption` because `adjustedHazardDamage` is blank for Heat.
- Flood should not show a meaningful magnitude-response curve when magnitudes/response are flat in the returned data.

## Commands Used

Build dashboard data:

```bash
/usr/bin/python3 scripts/build_dashboard_data.py \
  --physical docs/output_examples/asset_1232_physical_risks.xlsx \
  --transition docs/output_examples/asset_1232_transition_risks.xlsx \
  --out dashboard/data/example_asset_1232.json
```

Run local dashboard:

```bash
python -m http.server 8765
```

Open:

```text
http://localhost:8765/dashboard/
```

Syntax and builder checks:

```bash
node --check dashboard/assets/app.js
/usr/bin/python3 -m py_compile scripts/build_dashboard_data.py
git diff --check
```

Endpoint checks:

```bash
curl -sSf http://localhost:8765/dashboard/ >/tmp/scr_dashboard_index_check.html
curl -sSf http://localhost:8765/dashboard/assets/app.js | node --check --input-type=commonjs
```

Data count check:

```bash
curl -sSf http://localhost:8765/dashboard/data/example_asset_1232.json \
  | /usr/bin/python3 -c "import json,sys; d=json.load(sys.stdin); print(d['meta']['physical_rows'], d['meta']['transition_rows'], len(d['assets']))"
```

Expected:

```text
952 240 1
```

## Verification Performed

1. Confirmed dashboard endpoint loads.
2. Confirmed `dashboard/assets/app.js` parses with Node.
3. Confirmed `scripts/build_dashboard_data.py` compiles.
4. Confirmed sample JSON row counts:

```text
physical_rows = 952
transition_rows = 240
assets = 1
```

5. Confirmed direct-vs-market transition ranking facts:

```text
Direct_carbon_cost peak:
  Net Zero 2050 @ 2035 = 22.867987..., rating G

Market_demand_shifts peak:
  Current Policies @ 2040 = 7.422722..., rating B
```

6. Confirmed raw workbook Flood flatness:

```text
Flood adjustedHazardValueImpact = 0.000897112617182...
same across both scenarios and all future horizons
```

7. Confirmed Excel-to-JSON parity for hazard damage/disruption/value fields:

```text
0 inconsistent repeated metric groups
0 Excel-to-JSON parity errors
```

## Known Issues And Caveats

1. **Impact units need vendor confirmation**
   - Raw values are preserved.
   - Percent-style and basis-point displays are readability transforms only.

2. **A-G benchmark population is only partially understood**
   - Metadata says SCR reference infrastructure universe.
   - Need SCR confirmation before precise product copy.

3. **Magnitude-response plots are derived**
   - Useful for exploration.
   - Not confirmed vendor damage/vulnerability functions.

4. **Some curves are flat because SCR returned flat values**
   - Flood is the clearest example.
   - The dashboard now avoids exaggerating tiny floating-point variation.

5. **Database ingestion is not done**
   - The dashboard reads static JSON.
   - No InfraSure database tables or importer have been implemented yet.

## Useful Files To Read Next

```text
dashboard/README.md
dashboard/assets/app.js
scripts/build_dashboard_data.py
docs/output_examples/schema.md
docs/metadata/README.md
docs/guide.md
```

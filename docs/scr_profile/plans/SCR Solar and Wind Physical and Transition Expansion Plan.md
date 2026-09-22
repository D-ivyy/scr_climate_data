---
author: InfraSure
created: 2026-09-21
updated: 2026-09-22
status: active
---

# SCR Solar and Wind physical and transition expansion plan

## Current progress — 2026-09-22

| Phase | Status | Result |
|---|---|---|
| Phase 0: inventory and schema | Complete | Four surfaces reconciled; Wind complete, Solar missing the same 44 cells in both risk families |
| Phase 1: Wind physical investigation | Complete | 13,085 workbooks parsed; 11,968 usable factor cells; 1,117 metric-unavailable cells |
| Phase 2: Wind physical candidate | Complete as research package | Raw nulls preserved; 1,117 cells filled from nearest eligible Wind donors; filled V1 and stabilized V2 pass QA and are immutable under SCR `derived/` |
| Phase 3: transition deep profile | Next | Full-corpus transition grain, variability, and impact semantics |
| Phase 4: transition packages | Not started | Blocked by Phase 3 interpretation gate |
| Phase 5: recipient delivery/dashboard | Wind promotion pending | Wind research package is ready for recipient packaging; transition views remain blocked by Phase 3 |

## Outcome

Extend the governed SCR work from one completed Solar physical implementation
to a validated two-asset, two-risk-family package without mixing fundamentally
different risk concepts.

```text
                         SOURCE AND CONTRACT FREEZE
                                    |
                +-------------------+-------------------+
                |                                       |
                v                                       v
       WIND PHYSICAL BUILD                    TRANSITION INVESTIGATION
   parser -> factor -> stability           units -> grain -> variability
                |                                       |
                v                                       v
    PHYSICAL DELIVERY + UI              SOLAR + WIND TRANSITION CONTRACT
                |                                       |
                +-------------------+-------------------+
                                    |
                                    v
                      GOVERNED DELIVERY + DASHBOARD
```

## Scope

| Workstream | Starting state | Intended result |
|---|---|---|
| Solar physical | Existing governed delivery | Preserve; compare with current source before any refresh |
| Wind physical | Complete 13,085-workbook source | Canonical-grid EAL factor package using a validated method |
| Solar transition | 13,041-workbook source | Validated transition screening / stress package with explicit gaps |
| Wind transition | Complete 13,085-workbook source | Validated transition screening / stress package |

The plan covers source investigation, reproducible processing, QA, delivery
metadata, and dashboard integration. It does not create a combined physical +
transition score.

## Phase 0 — Freeze evidence and reconcile coverage

1. Inventory all four GCS prefixes by exact object URI and cell ID.
2. Compare each cell set with the authoritative 13,085-cell grid.
3. Record missing, extra, duplicate, and unreadable filenames.
4. Sample workbooks deterministically across the cell range.
5. Record sheet names, headers, row counts, dimensions, schema hashes, scenario
   sets, horizon sets, hazards, subrisks, indicators, and TICCS identity.
6. Preserve the difference between the existing Solar delivery source and the
   new current GCS surface.

Gate:

- exact cell-set reconciliation exists for all four surfaces;
- schema drift from older documentation is explicit; and
- no production logic relies on an untested old example.

Deliverables:

- discussion record;
- reproducible inventory/profile script;
- machine-readable inventory summary;
- Solar missing-cell list; and
- sampled schema profile.

## Phase 1 — Validate Wind physical as a new asset type

1. Reuse the Solar physical parser only where the current schema proves
   compatible.
2. Parse Wind `adjustedTotalDamage` with complete source provenance.
3. Derive same-scenario factors relative to 2025:

```text
raw factor = abs(future adjustedTotalDamage)
             --------------------------------
             abs(2025 adjustedTotalDamage)
```

4. Retain baseline magnitude, future magnitude, absolute change, raw factor,
   and status so every factor is reconstructible.
5. Profile the full factor distribution by scenario and horizon, including
   zero/tiny baselines, inversions, negative changes, extreme ratios, spatial
   clustering, and the maximum observed factor.
6. Run the existing Solar stabilization method on Wind as an experiment, then
   compare raw and stabilized spatial/rank behavior. Do not assume identical
   parameters are appropriate.

Gate:

- the full 13,085-cell Wind corpus has one parse outcome per workbook;
- raw factor arithmetic is reconstructible;
- any quarantined workbook is explained; and
- the selected applied factor is justified by comparative tests rather than
  copied from Solar by convention.

## Phase 2 — Build and publish the Wind physical package

1. Produce the canonical grain `cell_id x asset_type x scenario x horizon`.
2. Keep raw, stabilized/applied, and filled fields distinct.
3. Preserve raw null factors at the 1,117 cells without a usable 2025 baseline,
   but provide a separate nearest-metric-eligible Wind donor path for the
   complete-grid applied field. Record donor cell, distance, fill method, and
   explicit imputation status.
4. Add a sidecar with source inventory hash, schema hash, code revision,
   calibration parameters, QA results, and limitations.
5. Stage the package in the same governed delivery family as Solar physical,
   while preserving a clean asset-type dimension and release identity.
6. Update `current.delivery.yml` only after recipient QA passes.

Acceptance checks:

- 13,085 distinct canonical cells;
- two SSP scenarios and 16 future horizons;
- 418,720 unique delivery rows if every workbook passes;
- no noncanonical cells or duplicate grain;
- factor/status/provenance fields reconcile; and
- `factor_raw` retains 35,744 null rows while `factor_filled` has zero nulls;
- only EAL is eligible for scaling—PML, VaR, and TVaR remain out of scope.

## Phase 3 — Deep-profile transition risk before product design

1. Parse the current Solar and Wind transition corpora without interpreting the
   impact unit.
2. Confirm the complete scenario, horizon, indicator, subrisk, rating, and null
   domains across all workbooks.
3. Separate repeated row-level fields from true independent observations. In
   particular, do not add the same subrisk impact repeated on multiple
   indicator rows.
4. Quantify variation at each level:

```text
country -> scenario -> horizon -> asset type -> cell / asset
```

5. Test whether indicators are constant across cells while adjusted impacts or
   ratings vary by asset type/location.
6. Profile positive, negative, zero, blank, and extreme impacts by subrisk.
7. Validate the apparent schema identity:

```text
9 scenarios x 6 horizons x 4 indicators = 216 source rows/workbook
```

8. Resolve or explicitly preserve uncertainty around unit, denominator, sign,
   and the relationship between numeric impacts and A-G ratings.

Gate:

- the full-corpus grain and repetition rules are demonstrated;
- the product-safe interpretation is written down; and
- the team chooses one of these modes:

```text
A. rating / relative-screening delivery only
B. validated revenue / OpEx / cash-flow stress delivery
```

If the financial-impact semantics remain unresolved, the work proceeds only in
mode A; numeric impacts may be retained as raw evidence but not applied to cash
flow.

## Phase 4 — Define and build transition packages

The preferred product grain will be tested, not assumed. A likely compact
candidate is one row per:

```text
cell_id x asset_type x transition scenario x horizon
```

with wide columns for the four indicators, two subrisk impacts, two subrisk
ratings, and the overall transition rating. The raw normalized indicator grain
should remain available for audit.

Required fields include:

- canonical cell identity and coordinates;
- asset type and TICCS subclass;
- scenario pathway and horizon;
- raw and adjusted subrisk impacts with documented scale/status;
- subrisk and overall ratings;
- all four source indicators with source units;
- missing-source and interpretation-status flags; and
- source URI, schema hash, pipeline version, and creation time.

Solar's 44 missing cells must remain explicit. Any nearest-neighbor fill for a
transition value requires separate evidence because transition risk may be
country/sector/scenario driven rather than locally continuous.

Gate:

- package grain and units are unambiguous;
- Solar missingness treatment is approved;
- row counts and key uniqueness reconcile; and
- no raw impact is silently presented as a validated percentage or dollar loss.

## Phase 5 — Delivery and dashboard integration

1. Publish immutable releases plus recipient-facing README and QA sidecar.
2. Update delivery manifests only after staged validation.
3. Add an asset-type selector for Solar PV versus Onshore wind.
4. Keep Physical and Transition as separate product views.
5. Physical view: map the applied EAL factor/change with scenario and horizon
   controls and visible source status.
6. Transition view: scenario pathway, horizon, asset type, subrisk/overall
   rating, and—only if validated—cash-flow stress.
7. Use separate legends and scales; never imply that A-G transition ratings and
   physical EAL percentages are directly comparable.
8. Perform local and deployed smoke tests, including interactive values,
   filters, selected-cell paths, missingness labels, and manifest resolution.

## Execution environment

- Use local work only for inventory, small samples, schema design, and focused
  diagnostics.
- Use the existing Cloud Run / GCP batch pattern for full-corpus parsing and
  derived-package generation.
- Notebooks and investigation scripts produce evidence; production code owns
  governed releases.
- Use a clean worktree for Hazard_modeling delivery/dashboard changes because
  the current checkout contains unrelated work.

## Decision ledger

| Decision | Status | Evidence needed |
|---|---|---|
| Execute Wind physical before transition implementation | Approved workflow | Current source availability and reuse of known physical method |
| Keep physical and transition separate | Fixed | Different risk concepts and downstream financial uses |
| Reuse Solar parser structure for Wind | Conditional | Current schema and full-corpus validation |
| Reuse Solar stabilization parameters for Wind | Candidate supported | Wind experiment changes 307 valid rows, preserves identity band/order, and bounds candidate to 0.2089×–4.8921× |
| Fill 1,117 Wind metric-unavailable cells | Approved for separate applied field | Raw nulls and 48 late-emerging future rows remain intact; median donor distance 21.83 km, P95 35.25 km, maximum 86.55 km; 1,113 cells overlap the older Solar missing pattern |
| Treat transition impact as percentage | Open | SCR documentation or internal scale validation |
| Apply transition impact to cash flow | Open | Unit, denominator, sign, and combination rules |
| Fill Solar's 44 transition gaps spatially | Open | Demonstrated spatial continuity and product need |
| Refresh the existing Solar physical package | Deferred | Controlled old-vs-new source comparison |

## Definition of done

The expansion is complete only when:

1. all four source surfaces have frozen, reproducible inventories;
2. Wind physical has a validated canonical package and dashboard path;
3. transition semantics and grain are documented from current source evidence;
4. Solar and Wind transition packages pass recipient QA at the approved usage
   level;
5. immutable releases, manifests, READMEs, and limitations agree; and
6. the dashboard exposes the four quadrants without conflating their meanings.

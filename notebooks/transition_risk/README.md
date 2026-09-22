# SCR transition-risk investigation

This folder profiles current Solar PV and Onshore Wind transition workbooks
before InfraSure defines a financial application or delivery contract.

Execution order:

1. `00_sample_semantics_profile.py` — inspect deterministic current-source
   workbooks, extract the embedded ReadMe contract, test row repetition, compare
   location and asset-type variation, and produce a deduplicated candidate grain.
2. `01_template_fingerprint_sample.py` — sample both complete source ranges and
   detect distinct economic-output regimes before a full-corpus run.
3. Full-corpus extraction — freeze both source inventories and parse the 20-column
   output with `cloudrun/scr_transition_profile/run_task.py`, without converting
   impacts into cash-flow values.
4. Full-corpus variability profile — quantify what varies by country, scenario,
   horizon, asset type, and cell.
5. Contract decision — select rating-only screening or a validated financial
   stress representation after resolving scale and denominator questions.

The sample step writes:

- `outputs/<date>/transition_sample_semantics_profile.json`
- `outputs/<date>/transition_compact_sample.csv`
- `outputs/<date>/transition_template_fingerprint_sample.json`
- `outputs/<date>/transition_template_fingerprint_sample.csv`

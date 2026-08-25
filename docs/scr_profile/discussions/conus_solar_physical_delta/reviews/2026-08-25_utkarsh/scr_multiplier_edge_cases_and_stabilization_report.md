# SCR Solar CONUS: Zero-Baseline Hazard Genesis & Multiplier Stabilization Framework

---

## Executive Summary

Climate risk modeling for infrastructure and insurance portfolios frequently relies on **multiplicative damage scaling factors** (`Future EAL = Base EAL × Factor`). While multiplicative factors work effectively across typical distributions (0.50× to 2.00×), they suffer from fundamental mathematical and actuarial breakdowns in two critical boundary regimes:

1. **The Zero-Baseline Hazard Genesis Problem (Understated Catastrophe):** When a location has near-zero historical exposure to a peril (e.g., a coastal solar farm with $1 baseline flood risk) but faces catastrophic future emergence (e.g., permanent sea-level rise inundation causing $10M damage), any capped multiplier (such as 5.00×) predicts only $5 of future loss, completely missing a total site loss.
2. **The Microscopic Denominator Explosion (Outlier Instability):** Inversely, when baseline damage is trivially small (0.00001% of TIV), a modest physical change can generate synthetic raw multipliers exceeding 10,000×, distorting portfolio rollups if left unconstrained.

> ⚠️ **KEY TAKEAWAY:** A pure multiplier cannot solve both extremes simultaneously. Capping multipliers protects portfolios from artificial outlier explosions, but suppresses genuine emerging catastrophes on zero baselines. A hybrid additive-multiplicative framework is required.

---

## The Multiplier Regime Breakdown

| Risk Regime | Baseline Condition | Example Profile | Raw Multiplier | Standard 5× Cap Output | Actual Physical Loss | Assessment |
| :--- | :--- | :--- | :---: | :---: | :---: | :--- |
| **1. Zero-Baseline Genesis** | Negligible ($\approx \$0$) | Base: $10<br/>Future: $10,000,000 | 1,000,000× | **$50** | **$10,000,000** | ❌ **Severe Failure:** Misses total site destruction. |
| **2. Operational Range (99.8% of Grid)** | Non-trivial ($> \$500$) | Base: $100,000<br/>Future: $150,000 | 1.50× | **$150,000** | **$150,000** | ✅ **Accurate:** Smooth physical scaling. |
| **3. Microscopic Denominator** | Trace noise ($\approx \$0.02$) | Base: $0.02<br/>Future: $200 | 10,000× | **$0.10** | **$200** | ✅ **Stabilized:** Prevents false multibillion-$ portfolio spikes. |

---

## Details of the Two Core Failure Modes

### Failure Mode A: Zero-Baseline Hazard Genesis (Emerging Perils)
* **Context:** A solar asset is built inland from a tidal basin with negligible historical flood exposure (Base EAL = $10).
* **2100 Prediction:** Sea-level rise and coastal storm surge submerge the inverter pads, creating $10,000,000 in annual expected loss.
* **The Failure:**
  * `Raw Factor = $10,000,000 / $10 = 1,000,000×`
  * If capped or stabilized to 5.00×, the model outputs: `Projected Loss = $10 × 5.00 = $50`
  * **Result:** Underwriters remain completely blind to a catastrophic site wipeout.

### Failure Mode B: Microscopic Denominator Explosion (Synthetic Outliers)
* **Context:** A hyper-arid location experiences a tiny baseline wind-blown dust loss of $0.02.
* **Future Prediction:** A modeled convective gust increases annual loss to $200.
* **The Failure:**
  * `Raw Factor = $200 / $0.02 = 10,000×`
  * If applied indiscriminately across a portfolio, a 10,000× multiplier creates an artificial multibillion-dollar loss spike from a $200 physical movement.

---

## Role & Boundaries of Factor Stabilization (Arctangent Compression)

The **piecewise arctangent log transform** (`M_atan`) implemented in the V2 data delivery resolves Failure Mode B while preserving physical monotonicity:

* **Identity Zone (0.33× to 3.00×):** Raw factors remain completely untouched (`Applied Factor = Raw Factor`).
* **Upper Compression Zone (> 3.00×):** Compresses smoothly toward an asymptote ceiling of 5.00×.
* **Lower Compression Zone (< 0.33×):** Compresses smoothly toward a reciprocal floor of 0.20×.

> ℹ️ **STRENGTHS & LIMITS:**
> * **Where it succeeds:** For **99.84% of all CONUS cells**, baseline losses are sufficiently large (>$500) that arctangent compression smoothly bounds extreme volatility without causing rank reversals, temporal ties, or scenario inversions.
> * **Where it reaches mathematical limits:** For cells in the **Zero-Baseline Genesis Zone** (where baseline is <$100 or <0.0001% of TIV), *no multiplicative factor alone can produce an accurate dollar loss*. A complementary additive mechanism is required.

---

## The 4-Pillar Robustness Framework

### 1. Hybrid Multiplier + Additive Delta Model
To eliminate the zero-baseline blind spot, formulate projected physical loss as a hybrid composite:

$$\text{Future Total EAL} = (\text{Base EAL} \times \text{Factor}_{\text{stabilized}}) + \Delta\text{EAL}_{\text{emerging}}$$

* **`Base EAL × Factor_stabilized`** captures proportional scaling for existing, established hazards.
* **`ΔEAL_emerging = (Future Loss - Base Loss)`** applies when `Base Loss < $100`, capturing newly emergent risks in absolute dollar terms.

---

### 2. Hazard-Level Disaggregation (Independent Peril Scaling)
Composite multipliers must never be applied at the whole-facility level across uncorrelated hazards. Multipliers must be applied independently per peril:

$$\text{Total Future EAL} = \text{Future Flood} + \text{Future Wildfire} + \text{Future Hail} + \text{Future Wind}$$

#### Peril Isolation Principle:
* If a solar facility has **$500,000 baseline Wildfire EAL** and **$1 baseline Coastal Flood EAL**, an emerging flood risk factor of 5.00× scales only the $1 flood component to $5.
* It **does not scale** the $500,000 wildfire component to $2.5M, preventing false contamination of non-flood perils.

---

### 3. Low-Baseline Quarantine & Underwriting Guardrails (`near_zero_baseline`)
Establish an automated quarantine trigger in data feeds and UI dashboards:

* **Trigger:** `Baseline EAL_hazard < $100` (or `< 0.0001%` of TIV).
* **Automated Actions:**
  1. Set metadata flag: `near_zero_baseline = true`.
  2. Suppress the display of raw multipliers (`Factor > 1,000×`) in underwriting screens to prevent confusion.
  3. Default primary display to **Absolute Movement (`ΔEAL` in $)** rather than percentage change.
  4. Prompt underwriters: *"Emerging peril detected on zero historical baseline. Site-specific elevation survey required."*

---

### 4. Physical & Financial Boundary Constraints

* **Total Insured Value (TIV) Hard Ceiling:** Annual EAL and 500-Year PML cannot exceed 100% of asset replacement value:
  * `Projected Annual EAL ≤ 100% TIV`
  * `Projected RP500 PML ≤ 100% TIV`
* **Operational Asset Lifespan Clamping:** Solar PV infrastructure operates on a **25 to 35-year physical design lifecycle**:
  * Projects underwritten in 2025 will be decommissioned, repowered, or re-engineered by **2050–2060**.
  * Underwriting pricing should clamp operational projections at a **30-year maximum horizon (2055)**, reserving 2100 projections for long-term land-use planning.

---

## Numerical Case Studies: Comparison of Approaches

### Case A: Coastal Inundation on Zero Baseline (Emerging Peril)
* **Asset:** Coastal Solar PV ($148.3M TIV)
* **2025 Baseline Flood EAL:** $10 (negligible historical exposure)
* **2050 Modeled Flood Loss:** $5,000,000 (sea-level breach)

| Valuation Method | Applied Factor | Projected 2050 Flood Loss | Performance Assessment |
| :--- | :---: | :---: | :--- |
| **Pure Multiplier (Raw)** | 500,000× | $5,000,000 | Mathematically correct, but factor causes system overflow. |
| **Arctangent Capped (5.0×)** | 5.00× | $50 | ❌ **Severe Failure:** Misses $5M actual loss. |
| **Additive Delta Offset** | N/A | $5,000,000 | ✅ **Accurate:** Captures full physical loss movement. |
| **Hybrid Framework** | Flagged / Additive | **$5,000,000** | 🏆 **Optimal:** Quarantines factor, applies $5M delta. |

---

### Case B: Arid Wind Dust Outlier (Microscopic Denominator)
* **Asset:** Desert Solar PV ($148.3M TIV)
* **2025 Baseline Wind EAL:** $0.05
* **2050 Modeled Wind Loss:** $250 (minor gust anomaly)

| Valuation Method | Applied Factor | Projected 2050 Wind Loss | Performance Assessment |
| :--- | :---: | :---: | :--- |
| **Pure Multiplier (Raw)** | 5,000× | $250 | Multiplier creates false impression of catastrophic surge. |
| **Arctangent Capped (5.0×)** | 5.00× | $0.25 | Understates wind change by $249.75 (immaterial in $ terms). |
| **Hybrid Framework** | Flagged / Additive | **$250** | 🏆 **Optimal:** Suppresses 5,000× label, reflects $250 loss. |

---

### Case C: Standard High-Risk Facility (Established Peril)
* **Asset:** Central Plains Solar PV ($148.3M TIV)
* **2025 Baseline Hail EAL:** $850,000
* **2050 Modeled Hail Loss:** $1,700,000

| Valuation Method | Applied Factor | Projected 2050 Hail Loss | Performance Assessment |
| :--- | :---: | :---: | :--- |
| **Pure Multiplier (Raw)** | 2.00× | $1,700,000 | Accurate, within stable [0.33×, 3.00×] identity band. |
| **Arctangent Capped** | 2.00× | $1,700,000 | Unchanged, perfect identity match. |
| **Hybrid Framework** | 2.00× | **$1,700,000** | 🏆 **Optimal:** Standard multiplicative scaling. |

---

## Production Decision & Implementation Matrix

| Metric / Parameter | Implementation Rule | Rationale |
| :--- | :--- | :--- |
| **Normal Operational Zone** (`Base ≥ $100`) | Apply Arctangent Stabilized Factor (`M_atan`). | Preserves 100% of physical monotonicity without rank reversals. |
| **Zero-Baseline Quarantine** (`Base < $100`) | Suppress multiplier; apply Additive Delta Offset (`ΔEAL`). | Prevents understating emerging catastrophic perils. |
| **Hazard Disaggregation** | Calculate factors independently per peril before aggregation. | Prevents cross-peril baseline contamination. |
| **Portfolio Aggregation** | Roll up absolute dollar losses (`∑ EAL_USD`), never average multipliers. | Multiplier averaging introduces fatal denominator weighting biases. |
| **Underwriting Horizon** | Clamp operational solar assets at 30-year operational horizon (2055). | Reflects actual equipment service life and repowering cycles. |
| **Physical Ceilings** | Hard-cap annual EAL and 500-year PML at 100% TIV. | Prevents modeled losses from exceeding asset replacement value. |

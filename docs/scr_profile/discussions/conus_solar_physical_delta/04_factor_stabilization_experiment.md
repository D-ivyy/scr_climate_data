# SCR Solar overall-factor stabilization experiment

**Status:** investigation only; no production factor has been changed
**Data tested:** 11,928 observed Solar PV cells, 2 scenarios, 16 horizons
**Raw maximum:** 1,556.7451×

## Question

Can an overall SCR damage factor be transformed into a numerically stable EAL
multiplier without moving to a full hazard-level financial calculation, and
without materially changing the ordinary part of the SCR distribution?

## Required behavior

The preferred method should:

1. preserve factors in the ordinary range;
2. preserve ordering across cells, horizons, and scenarios;
3. control both the upper and lower extreme tails;
4. avoid inventing values from neighboring cells;
5. remain auditable and reversible to the raw SCR result; and
6. expose any ceiling as an explicit InfraSure policy choice.

## Methods tested

The experiment compared:

- raw SCR ratio;
- hard factor cap;
- square-root/power compression;
- symmetric plain-log compression;
- a `1e-4` denominator floor;
- smooth log-space ceilings with several start and ceiling values;
- a 3×3 spatial ratio of medians; and
- spatial replacement only for isolated outliers.

The test is reproducible through
`notebooks/conus_solar_physical_delta/03_factor_stabilization_experiment.py`.

## Main comparison

| Method | Share of all rows changed | Core distortion (`0.5×–2×`) | Global maximum | Temporal reversals | Scenario reversals | Assessment |
|---|---:|---:|---:|---:|---:|---|
| Raw | 0% | 0 | 1,556.75× | 0 | 0 | Unsafe as direct multiplier |
| Hard cap at 5× | 0.094% | 0 | 5.00× | 0 | 0 | Creates 287 temporal and 73 scenario ties |
| Square root | 61.65% | 0.0184 log error | 39.46× | 0 | 0 | Changes far too much of the distribution |
| Symmetric plain log | 61.41% | 0.0026 log error | 8.35× | 0 | 0 | Changes ordinary values and has no explicit policy ceiling |
| Baseline floor `1e-4` | 20.69% | 0.0116 log error | 61.36× | 0 | 29 | Does not solve the tail and can reverse scenario ordering |
| Spatial ratio, all cells | 57.29% | 0.0092 log error | 18.05× | 9,988 | 6,342 | Excessive smoothing and ordering changes |
| Spatial outlier replacement | 0.068% | 0 | 18.80× | 57 | 94 | Useful QA signal, but not a clean applied-factor rule |
| Soft log, start 2× / ceiling 5× | 0.289% | effectively 0 | 5.00× | 0 | 0 | Strong candidate, but begins earlier than necessary |
| Soft log `tanh`, start 3× / ceiling 5× | 0.164% | 0 | 5.00× | 0 | 0 | Strong, but floating-point saturation can merge the most extreme values |
| **Soft log `arctan`, start 3× / ceiling 5×** | **0.164%** | **0** | **4.916× observed; 5× asymptote** | **0** | **0** | **Best numerical candidate tested** |

“Ordering ties” are separated from reversals. A hard cap has no reversals, but
it collapses distinct raw values to the identical ceiling. The arctangent soft
ceiling preserves strict ordering across all tested distinct factors.

### QA refinement after the first V2 build attempt

The initial V2 build used the `tanh` soft ceiling. Its release QA stopped the
build before publication because sufficiently large finite inputs can become
numerically indistinguishable near the asymptote in float64. The candidate was
therefore changed to an arctangent saturation curve and the full experiment was
rerun. The arctangent version retains the same identity band and bound, but
approaches the ceiling more slowly and preserved strict factor ordering in the
complete tested dataset.

## Why the arctangent 3×/5× candidate performed best

At 2100, the raw P99.5 is approximately:

- SSP2-4.5: `3.105×`
- SSP5-8.5: `2.717×`

Starting compression at `3×` therefore leaves approximately the first 99.5%
of the distribution substantively untouched while targeting the unstable
tail. Starting at `2×` changes almost twice as many rows across the complete
scenario/horizon dataset.

The candidate transform is symmetric and piecewise:

```text
F = raw factor
T = 3.0 (compression start)
C = 5.0 (soft ceiling)

If 1/T <= F <= T:
    F_applied = F

If F > T:
    a = ln(T)
    b = ln(C)
    u = (ln(F)-a)/(b-a)
    g = (2/pi) * atan((pi/2) * u)
    F_applied = exp[a + (b-a) * g]

If F < 1/T:
    F_applied = 1 / SoftUpper(1/F, T, C)
```

Mapping examples:

| Raw factor | Applied candidate |
|---:|---:|
| 0.039× | 0.210× |
| 0.10× | 0.218× |
| 0.20× | 0.240× |
| 0.50× | 0.50× |
| 1.00× | 1.00× |
| 2.00× | 2.00× |
| 3.00× | 3.00× |
| 5.00× | 4.158× |
| 10.00× | 4.589× |
| 25.00× | 4.759× |
| 100.00× | 4.852× |
| 1,556.75× | 4.916× |

```text
Applied factor

5× |                            ............. soft ceiling
   |                       .....
4× |                  .....
   |               ...
3× |--------------● compression begins
   |             /
2× |-----------●
   |         /
1× |-------●
   +------------------------------------------------> Raw factor
           1×    2×    3×    5×    10×   100×  1,556×
```

## 2100 distribution after the 3×/5× transform

| Scenario | Raw P99 | Raw P99.5 | Raw P99.9 | Raw maximum | Applied P99 | Applied P99.5 | Applied P99.9 | Applied maximum |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| SSP2-4.5 | 1.832× | 3.105× | 11.915× | 649.43× | 1.832× | 3.105× | 4.637× | 4.903× |
| SSP5-8.5 | 1.977× | 2.717× | 19.949× | 1,556.75× | 1.977× | 2.717× | 4.731× | 4.916× |

## Financial stress test

The experiment tested baseline EAL rates from `0.1%` through `10%` of TIV.
With the 5× soft ceiling:

- a 1% baseline EAL rate cannot exceed approximately 5% through this factor;
- a 2% baseline EAL rate cannot exceed approximately 10%;
- a 5% baseline EAL rate cannot exceed approximately 25%; and
- a 10% baseline EAL rate cannot exceed approximately 50%.

This is a mathematical bound, not evidence that 5× is economically correct.
An application-level EAL/TIV validation remains required.

## What the test establishes

Among the methods tested, a piecewise arctangent soft ceiling in log-factor
space is the cleanest numerical approach because it:

- leaves ordinary factors exactly unchanged;
- changes only 0.164% of all tested rows at the 3×/5× settings;
- preserves time and scenario ordering;
- retains distinctions within the tail instead of creating a pile-up at 5×;
- avoids replacing a location with its neighbors; and
- gives InfraSure explicit and auditable control over the allowed factor range.

## What the test does not establish

This experiment cannot establish that `3×` and `5×` are economically or
scientifically correct. There is no observed future-loss ground truth in the
SCR exports. The start and ceiling are policy/calibration parameters, not
facts learned from the raw ratio distribution.

Before production approval, the following remain necessary:

1. apply the candidate to representative InfraSure Solar EAL/TIV records;
2. inspect every affected Solar cell and its full time trajectory on a map;
3. repeat the distribution test for Wind and Gas before adopting a universal
   parameter set;
4. decide whether the reciprocal lower floor of `0.20×` is acceptable; and
5. obtain team approval for the `5×` maximum applied factor.

## Current recommendation

Do not modify the V1 Parquet yet. Preserve `factor_raw` as the research result.
Carry the **arctangent soft-log 3×/5× method forward as the leading candidate**,
alongside the raw factor and QA flags, for asset-level EAL/TIV testing. Spatial
and hazard-level findings should remain diagnostic fields rather than silent
value replacement rules.

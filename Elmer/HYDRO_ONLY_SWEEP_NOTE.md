# Hydro-Only Sweep Diagnostics

Date: 2026-08-04

## Scope

A hydro-only sweep was run using `run_hydro_only_sweep.py` over:

- sign mode: `negative`, `positive`
- pressure datum: `0.0`, `2.0`, `4.0`, `6.0` m
- boundary mode: `correct_b2`, `swapped_b3`, `both_b2_b3`
- truncation mode: `indicator`, `max`

All cases used:

- gravity off
- crest surcharge off
- upstream head = 29 m

## Key findings

1. Truncation mode had no effect in this model (`indicator` and `max` returned identical stresses for each case).
2. Boundary targeting mode is the dominant hydro sensitivity:
   - `correct_b2` and `swapped_b3` produce very large stress magnitudes and poor target match.
   - `both_b2_b3` dramatically reduces peak stresses and gives the lowest combined deviation from target.
3. Sign mode swaps where high compression appears (upstream/downstream orientation effect), but does not resolve the compression underprediction when `both_b2_b3` is used.
4. Best hydro-only case by combined absolute delta:
   - `hydro_negative_datum_6p0m_both_b2_b3_indicator`
   - tension = 0.6489 MPa, compression = -1.6774 MPa
   - combined delta = 2.2037 MPa

## Interpretation

Hydro-only loading cannot reproduce both client targets simultaneously in this simplified model. The nearest hydro-only matches still underpredict compression magnitude versus the client expectation of -3.33 MPa.

The run supports the earlier conclusion that expected-case comparability depends on full load-combination definition and/or structural restraint realism, not hydrostatic expression details alone.

## Output references

- `hydro_sweep/hydro_only_sweep.csv`
- `hydro_sweep/hydro_only_sweep.json`
- `hydro_sweep/sif_cases/*.sif`
- `results_hydro_sweep/*`

# Combined Gravity+Hydro Sweep Diagnostics

Date: 2026-08-04

## Scope

Focused 16-case sweep run via `run_combined_gravity_hydro_sweep.py`:

- gravity: on for all cases
- hydrostatic: on for all cases
- crest surcharge: off/on per candidate
- hydro candidates: top shortlist from hydro-only sweep (both-face boundary mode only)

## Best combined cases (lowest combined delta to +1.20 / -3.33 MPa)

1. `combo_positive_datum_0p0m_both_b2_b3_indicator_crest_off`
   - tension = 1.948 MPa
   - compression = -0.763 MPa
   - combined delta = 3.315 MPa
2. `combo_negative_datum_6p0m_both_b2_b3_indicator_crest_off`
   - tension = 0.263 MPa
   - compression = -0.925 MPa
   - combined delta = 3.342 MPa

## Key findings

1. Combined sweep does not improve over gravity-only baseline in terms of matching both client targets simultaneously.
2. All shortlisted combined cases still underpredict compression magnitude substantially relative to -3.33 MPa.
3. Crest surcharge toggle has small effect only:
   - some negative-sign candidates improve slightly with crest on
   - most positive-sign candidates worsen slightly with crest on
4. Best overall case remains a compromise with either:
   - tension above target and compression too small in magnitude, or
   - tension below target and compression still too small in magnitude.

## Interpretation

Within this focused hydro formulation family (`both_b2_b3` variants), adding gravity and crest does not recover the missing compressive demand. This points to model physics outside this load-expression space (restraint realism/foundation representation and/or missing load actions) as the dominant remaining gap.

## Output references

- `combined_sweep/gravity_hydro_combined_sweep.csv`
- `combined_sweep/gravity_hydro_combined_sweep.json`
- `combined_sweep/sif_cases/*.sif`
- `results_combined_sweep/*`

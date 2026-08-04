# Client-Facing Mismatch Uncertainty Table

Date: 2026-08-04

Targets used for all deltas:

- Tension target: +1.20 MPa
- Compression target: -3.33 MPa
- Combined mismatch score: |tension - 1.20| + |compression + 3.33|

## Executive summary

- The restraint-model sweep produced the strongest improvement versus the prior best load-only combined case.
- Best current score comes from a very soft base + stiffer abutments envelope.
- In the uplift small matrix, changing uplift head did not change stresses within each restraint envelope (zero within-envelope spread), indicating uplift as currently implemented is not yet an active differentiator.

## Uncertainty separation table

| Uncertainty source | Sweep file | Fixed assumptions | Best case | Best tension (MPa) | Best compression (MPa) | Best score | Score range in sweep | Spread |
|---|---|---|---|---:|---:|---:|---:|---:|
| Load-definition uncertainty | combined_sweep/gravity_hydro_combined_sweep.csv | Baseline restraints (1.0x/1.0x) | combo_positive_datum_0p0m_both_b2_b3_indicator_crest_off | 1.948 | -0.763 | 3.314935 | 3.314935 to 3.926308 | 0.611373 |
| Restraint-model uncertainty | restraint_sweep/restraint_model_sweep.csv | Fixed best load definition | restraint_base_0p1x_abut_3p0x | 3.144 | -3.251 | 2.022256 | 2.022256 to 3.376789 | 1.354533 |
| Uplift block matrix (small) | uplift_matrix/uplift_small_matrix.csv | Fixed load definition + 3 restraint envelopes | uplift_soft_head_0p0m (same as all soft uplift heads) | 2.171 | -1.670 | 2.631182 | 2.631182 to 3.314935* | 0.683753* |

*The uplift matrix range reflects differences between restraint envelopes; uplift-head variation within each envelope is 0.000000 spread.

## Best cases by sweep

### 1) Load-definition sweep best

- Case: `combo_positive_datum_0p0m_both_b2_b3_indicator_crest_off`
- Tension: 1.948157 MPa
- Compression: -0.763222 MPa
- Score: 3.314935

### 2) Restraint sweep best

- Case: `restraint_base_0p1x_abut_3p0x`
- Base spring scale: 0.1x
- Abutment spring scale: 3.0x
- Tension: 3.143664 MPa
- Compression: -3.251407 MPa
- Score: 2.022256

### 3) Uplift small matrix best per envelope

- Soft (0.3x/0.3x): score 2.631182 (all uplift heads identical)
- Baseline (1.0x/1.0x): score 3.314935 (all uplift heads identical)
- Stiff (10x/10x): score 3.270998 (all uplift heads identical)

## Interpretation for client discussion

1. Restraint idealization uncertainty is currently larger than load-definition uncertainty in terms of score spread.
2. Current model can be tuned toward compression magnitude by changing restraint envelope, but this can drive tension away from target.
3. Uplift block inclusion exists in the model setup, but uplift-head variation did not change outcomes in this matrix and should be treated as a model-behavior check item before using it as a calibration lever.

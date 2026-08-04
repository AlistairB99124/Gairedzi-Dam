# Hydro Retune Candidate Comparison (5 Cases)

Date: 2026-08-04

Target metrics:

- Max tension: +1.20 MPa
- Max compression: -3.33 MPa
- Score: |tension - 1.20| + |compression + 3.33|

Method:

- Starting point: hardened `dam_model.sif` hydro formulation using `Normal Force` and indicator truncation.
- 5 candidate settings were solved against the same mesh and support setup.

## Candidate table

| Rank | Case | Upstream free-surface z (m) | Downstream free-surface z (m) | Hydro scale | Max tension (MPa) | Max compression (MPa) | Score |
|---|---|---:|---:|---:|---:|---:|---:|
| 1 | c5_fs24_scale0p15 | 24.0 | 1.5 | 0.15 | 2.219 | -0.930 | 3.420 |
| 2 | c4_scale_0p10 | 29.0 | 2.0 | 0.10 | 2.728 | -1.238 | 3.621 |
| 3 | c3_scale_0p15 | 29.0 | 2.0 | 0.15 | 3.468 | -1.618 | 3.980 |
| 4 | c2_scale_0p25 | 29.0 | 2.0 | 0.25 | 4.948 | -2.380 | 4.698 |
| 5 | c1_baseline | 29.0 | 2.0 | 1.00 | 16.052 | -8.097 | 19.620 |

## Recommendation applied to dam_model.sif

The best compromise in this 5-case set is:

- upstream free-surface z = 24.0 m
- downstream free-surface z = 1.5 m
- hydro scale factor = 0.15

These settings were applied to `Elmer/dam_model.sif`.

## Practical interpretation

- This retune substantially reduces the severe tension overshoot introduced by the fully active baseline hydro setup.
- Compression magnitude is still materially below the client target (-3.33 MPa), so this should be treated as an interim calibration compromise, not final match.

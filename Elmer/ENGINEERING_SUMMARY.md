# Arch Dam Engineering Summary

## Current Conclusions

- A major earlier mismatch was caused by gravity being applied on the wrong axis; correcting gravity to the vertical Z axis brought tensile stress back into the expected range.
- With the corrected model, the current refined baseline result is approximately `1.147 MPa` maximum tensile principal stress and `-0.557 MPa` maximum compressive principal stress.
- The tensile result is close to the client's expected `1.2 MPa`.
- The compressive result remains well below the client's expected `-3.33 MPa`.
- Pressure-face targeting has been numerically checked on the converted Elmer mesh; upstream and downstream hydraulic faces are assigned to opposite radial faces as intended.
- A downstream tailwater sweep from `0 m` to `29 m` produced no change in the reported peak tensile or compressive stresses in the current simplified model.

## Current Model State

- Uniform wall thickness is `4.0 m` through most of the section.
- A crest-thickening surrogate adds `1.0 m` over the top `2.0 m` of wall height.
- The model includes compliant base springs and explicit abutment spring restraints.
- The model still omits galleries, fillets, detailed abutment transition stiffening, and richer foundation interaction.

## Current Reference Outputs

- Stress summary: `Elmer/results/stress_summary.json`
- Stress plot: `Elmer/results/principal_stress_distribution.png`
- Critical locations: `Elmer/results/critical_stress_locations.png`
- Client report sheet: `Elmer/results/client_stress_report.png`
- Load-case sweep: `Elmer/sweep_results/load_case_comparison.csv`

## Next Moves

1. Build an explicit load-combination matrix with the client so the expected `-3.33 MPa` compression case is defined unambiguously.
2. Replace the current spring-based abutment/foundation surrogate with a more realistic structural restraint model.
3. Revisit hydraulic loading beyond the current simplified pressure surrogates, especially if the client expectation includes additional actions such as uplift, thermal, silt, or a different downstream condition.
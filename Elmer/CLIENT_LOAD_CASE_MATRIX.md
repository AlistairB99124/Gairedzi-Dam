# Client Load-Case Definition Matrix (Locked Inputs for Calibration)

Date: 2026-08-04

Purpose: freeze the target load definition used for stress calibration, and capture any remaining client confirmations needed before sign-off.

## Governing calibration targets

- Target maximum tensile principal stress: +1.20 MPa
- Target maximum compressive principal stress: -3.33 MPa

## Load and support matrix

| Block | Current calibration value | Included in baseline | Status |
|---|---:|---|---|
| Gravity acceleration | 9.81 m/s^2 (vertical Z) | Yes | Locked |
| Concrete density | 2400 kg/m^3 | Yes | Locked |
| Upstream head | 29.0 m | Yes | Locked |
| Pressure datum elevation | +4.0 m (mesh datum) | Yes | Locked |
| Upstream peak pressure at datum | 284,490 Pa | Yes | Locked |
| Downstream tailwater head | 2.0 m | Yes | Locked |
| Crest surcharge head | 2.0 m | Yes | Locked |
| Water density | 1000 kg/m^3 | Yes | Locked |
| Base restraint | Springs: [1e10, 1e10, 5e10] N/m^3 | Yes | Locked |
| Abutment restraint | Springs: [1e11, 1e11, 5e10] N/m^3 | Yes | Locked |
| Material E | 35 GPa | Yes | Locked |
| Material nu | 0.20 | Yes | Locked |

## Explicit formulation assumptions used in calibration SIF generation

- Hydrostatic traction is applied as Normal Force on boundary sets 2 and 3.
- Vertical coordinate for pressure truncation is Coordinate 3 (Z).
- Free-surface elevations are computed as pressure_datum_z_m + head_m.
- Crest block is represented as constant normal force from crest_head_m.

## Confirmations required from client to finalize expected-case comparability

1. Confirm whether the -3.33 MPa compression expectation includes only gravity + hydrostatic + crest surcharge, or includes additional actions (uplift, thermal, silt, seismic, staged construction effects).
2. Confirm downstream condition for the expected case (tailwater magnitude and whether transient or steady state).
3. Confirm datum reference used in the client pressure calculations relative to the modeled mesh elevation origin.
4. Confirm whether restraint conditions are intended to represent rigid bedrock, springs, or foundation continuum behavior.
5. Confirm whether reported client stresses are local peak values, averaged values, or envelope values from multiple load combinations.

## Notes

- This matrix reflects the configuration in calibration_case.json and generated calibration SIF files.
- Any change to a Locked input should trigger re-run of calibration sweeps and update of this document revision.

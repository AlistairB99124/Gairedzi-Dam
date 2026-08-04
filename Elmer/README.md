# Elmer curved dam starter model

This folder contains a first-pass workflow for a curved concrete dam based on the client data in the Data folder.

## What is included

- build_curved_dam_geometry.py: reads Data/Dam_Base_Contours.json and generates a simple curved centerline geometry plus a Gmsh .geo file.
- load_cases.json: stores the material properties, thickness, gravity, water level, overflow head, and boundary-condition assumptions.
- dam_model.sif: starter Elmer input template for a 3D structural model with gravity, hydrostatic pressure, and a rigid-bedrock base.

## Notes

- The geometry is a first-order surrogate because no drawing was provided.
- The flat segment in the middle of the profile is preserved as a horizontal plateau in the generated geometry.
- For a realistic cracking assessment, the starter model should later be upgraded to a nonlinear concrete damage material model rather than a simple elastic one.

## Benchmark calibration workflow

- Use `build_calibration_sif.py` to generate a dedicated calibration model (`dam_model_calibration.sif`) without changing `dam_model.sif`.
- Edit `calibration_case.json` to toggle gravity, hydrostatic loads, crest surcharge, and support style (`spring` or `fixed`).
- Set `water.pressure_datum_z_m` so hydrostatic pressure is referenced to the intended elevation datum.
- Optional: set `water.target_peak_upstream_pressure_pa` for a sanity warning if it does not match `rho*g*upstream_head_m`.
- Run: `python3 build_calibration_sif.py`
- Solve the generated case with ElmerSolver using `dam_model_calibration.sif`.

### Optional datum/head sweep

- Run `python3 sweep_calibration_datum_head.py` to generate a small matrix of calibration SIF files while varying only:
	- `water.pressure_datum_z_m`
	- `water.upstream_head_m`
- Add `--run-solver` to execute ElmerSolver and stress post-processing per case, appending `max_tension_mpa` and `max_compression_mpa` columns.
- If ElmerSolver is not in PATH, pass `--solver-exe /path/to/ElmerSolver`.
- Optional solver environment flags: `--elmer-home` and `--elmer-modules-path`.
- Outputs:
	- `calibration_sweeps/datum_head_sweep.csv`
	- `calibration_sweeps/datum_head_sweep.json`
	- `calibration_sweeps/sif_cases/*.sif`

# Gairedzi Dam Structural Analysis (Elmer FEM)

This repository contains a first-pass structural analysis workflow for a curved concrete arch dam using Elmer FEM.

The project combines:

- client/source data in `Data/`
- procedural geometry + mesh generation in `Elmer/`
- solver setup and post-processing for tensile/compressive principal stress

## Project Status

Current model and tooling are suitable for rapid engineering iteration and comparison studies.

Latest validated baseline (from `Elmer/results/stress_summary.json`):

- max tensile principal stress: about `+1.147 MPa`
- max compressive principal stress: about `-0.557 MPa`

Interpretation:

- tensile stress is close to the expected benchmark (~`1.2 MPa`)
- compressive stress is currently lower in magnitude than expected (`-3.33 MPa` target case), indicating model/load-case simplifications still dominate compression behavior

## Repository Structure

```text
Data/
  Computational_Grid_Controls.json
  Concrete_Material_Properties.json
  Dam_Base_Contours.json
  Env_Boundaries_And_Loads.json
  ...

Elmer/
  build_curved_dam_geometry.py
  dam_model.sif
  analyze_stress.py
  sketch_arch_dam_views.py
  run_load_case_sweep.py
  load_cases.json
  results/
  sweep_results/

.vscode/
  tasks.json
```

## What the Workflow Does

1. Builds a curved dam wall mesh from base contour data.
2. Solves linear elastic 3D structural response in Elmer under gravity + hydrostatic-style loads.
3. Post-processes VTU displacement output into stress tensors and principal stresses.
4. Produces engineering plots and summary files for review.

## Model Highlights

- nominal wall thickness set to `4.0 m`
- crest-thickening surrogate: `+1.0 m` over top `2.0 m`
- explicit upstream/downstream/base/crest boundary faces in mesh
- compliant support treatment via springs at base/abutments
- gravity axis corrected to vertical `Z` (critical fix made during development)

## Requirements

- Python 3.10+
- Elmer FEM installation with:
  - `ElmerGrid`
  - `ElmerSolver`
- Python packages:
  - `numpy`
  - `matplotlib`

Note: current scripts/task file use local Elmer paths under `/Users/alistairdavies/elmerfem`. If your install path differs, update:

- `.vscode/tasks.json`
- `Elmer/run_load_case_sweep.py`

## Quick Start

### Option A: VS Code task

Run task:

- `Elmer: build dam VTU`

This performs geometry build, mesh conversion, and solver run.

### Option B: Manual commands

From repository root:

```bash
cd Elmer
rm -rf mesh results
mkdir -p mesh results
python3 build_curved_dam_geometry.py
/Users/alistairdavies/elmerfem/bin/ElmerGrid 14 2 curved_dam_mesh.msh -autoclean -out mesh
ELMER_HOME=/Users/alistairdavies/elmerfem \
ELMER_MODULES_PATH=/Users/alistairdavies/elmerfem/share/elmersolver/lib \
/Users/alistairdavies/elmerfem/bin/ElmerSolver dam_model.sif
```

## Stress Post-Processing

After solver completion:

```bash
cd Elmer
python3 analyze_stress.py
```

Primary outputs:

- `Elmer/results/principal_stress_by_element.csv`
- `Elmer/results/stress_summary.json`
- `Elmer/results/principal_stress_distribution.png`
- `Elmer/results/critical_stress_locations.png`
- `Elmer/results/client_stress_report.png`

## Orientation Sketches

Generate architect-style orientation views:

```bash
cd Elmer
python3 sketch_arch_dam_views.py
```

Output:

- `Elmer/results/arch_dam_orientations.png`

## Load-Case Sweep

Run downstream tailwater sensitivity sweep:

```bash
cd Elmer
python3 run_load_case_sweep.py
```

Outputs:

- `Elmer/sweep_results/load_case_comparison.csv`
- `Elmer/sweep_results/load_case_comparison.json`
- per-case stress summaries and plots under `Elmer/sweep_results/<case_name>/`

## Engineering Notes and Limitations

This is a structured first-order model, not a final design-basis digital twin. Current simplifications include:

- linear elastic concrete
- surrogate crest detailing
- simplified foundation/abutment interaction
- no explicit galleries, contraction joints, fillets, uplift modeling, thermal loading, or nonlinear cracking/damage

These simplifications are expected to affect compressive stress distribution and peak values.

## Recommended Next Steps

1. Align a formal load-combination matrix with the client for the target compression benchmark.
2. Upgrade support/foundation representation beyond spring surrogates.
3. Add additional load mechanisms (uplift, thermal, silt/operational variants as required).
4. Perform mesh-convergence checks specifically on principal stress peaks.
5. Progress to nonlinear material/damage modeling for cracking risk studies.

## Additional Documentation

- `Elmer/ENGINEERING_SUMMARY.md` for current conclusions and recorded next moves.

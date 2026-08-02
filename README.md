# Gairedzi Dam Structural Analysis (Elmer FEM)

This repository contains a first-pass structural analysis workflow for a curved concrete arch dam using Elmer FEM.

## Versioning

This project uses a client-friendly semantic version strategy:

- Major.Minor.Patch (example: 1.2.0)
- Major: workflow changes that may affect client usage
- Minor: new features and automation improvements
- Patch: bug fixes and reliability improvements

Version files:

- `VERSION`: current client-facing version
- `RELEASE_NOTES.md`: plain-language summary of changes

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

## One-Click Client Runner (Windows - recommended)

For non-technical use on Windows, use:

- `run.bat` (main entry point)

Setup and run are now separated:

- `Setup/setup.bat`: installs prerequisites only (Python deps and Elmer)
- `run.bat`: runs analysis and calls setup only if required
- `Run_Gairedzi.bat`: compatibility wrapper that calls `run.bat`
- `update.bat`: updates from GitHub for both cloned repos and ZIP-downloaded folders
- `VERSION`: current release number shown by run and update scripts

What it does automatically:

1. checks for Python and installs it with winget if needed
2. creates/updates `.venv`
3. installs Python dependencies (`numpy`, `matplotlib`)
4. checks for Elmer (`ElmerGrid`, `ElmerSolver`)
5. attempts winget-based Elmer install if Elmer is missing
6. rebuilds geometry/mesh from current `Data/` files
7. runs Elmer solver and stress post-processing
8. opens the client stress report image when finished

Client workflow (Windows):

1. update raw input data under `Data/`
2. double-click `run.bat`
3. wait for completion and review:
   - `Elmer/results/client_stress_report.png`
   - `Elmer/results/stress_summary.json`

Important notes:

- first run may show Windows prompts for installation permissions
- internet access is required for first-time dependency installation
- if winget cannot install Elmer automatically, install Elmer manually and ensure `ElmerGrid` and `ElmerSolver` are in PATH

Run logs are saved under `results/logs/` for traceability and reproducibility.

## One-Click Client Runner (macOS)

If you also run the model on macOS, use:

- `Setup/Run_Gairedzi.command`

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

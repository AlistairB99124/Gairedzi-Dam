from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from build_calibration_sif import build_sif
from run_hydro_only_sweep import make_pressure_expr, rewrite_hydro_boundaries
from sweep_calibration_datum_head import ROOT, pick_solver_executable, run_solver_and_postprocess

SWEEP_DIR = ROOT / "uplift_matrix"
SIF_DIR = SWEEP_DIR / "sif_cases"
CSV_PATH = SWEEP_DIR / "uplift_small_matrix.csv"
JSON_PATH = SWEEP_DIR / "uplift_small_matrix.json"

DEFAULT_EXPECTED_TENSION_MPA = 1.2
DEFAULT_EXPECTED_COMPRESSION_MPA = -3.33

FIXED_LOAD_CASE = {
    "sign_mode": "positive",
    "datum_m": 0.0,
    "boundary_mode": "both_b2_b3",
    "truncation_mode": "indicator",
    "include_crest": False,
}

RESTRAINT_ENVELOPES = [
    {"name": "soft", "base_scale": 0.3, "abutment_scale": 0.3},
    {"name": "baseline", "base_scale": 1.0, "abutment_scale": 1.0},
    {"name": "stiff", "base_scale": 10.0, "abutment_scale": 10.0},
]

UPLIFT_HEAD_VALUES_M = [0.0, 5.0, 10.0, 20.0, 29.0]


def load_base_config() -> dict:
    return json.loads((ROOT / "calibration_case.json").read_text())


def case_name(envelope_name: str, uplift_head_m: float) -> str:
    h = f"{uplift_head_m:.1f}".replace(".", "p")
    return f"uplift_{envelope_name}_head_{h}m"


def run(
    run_solver: bool,
    solver_exe: str | None,
    elmer_home: str | None,
    elmer_modules_path: str | None,
    expected_tension_mpa: float,
    expected_compression_mpa: float,
) -> None:
    base_cfg = load_base_config()

    rho_water = float(base_cfg["water"]["density_kg_m3"])
    gravity = float(base_cfg["water"]["gravity_m_s2"])
    upstream_head_m = float(base_cfg["water"]["upstream_head_m"])

    base_springs_nominal = [float(x) for x in base_cfg["support"]["base_spring"]]
    abutment_springs_nominal = [float(x) for x in base_cfg["support"]["abutment_spring"]]

    resolved_solver = None
    if run_solver:
        resolved_solver = pick_solver_executable(solver_exe)
        if resolved_solver is None:
            raise FileNotFoundError("ElmerSolver executable not found. Pass --solver-exe or add ElmerSolver to PATH.")

    SWEEP_DIR.mkdir(parents=True, exist_ok=True)
    SIF_DIR.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, float | str | bool]] = []

    for envelope in RESTRAINT_ENVELOPES:
        for uplift_head_m in UPLIFT_HEAD_VALUES_M:
            case = case_name(str(envelope["name"]), uplift_head_m)
            cfg = json.loads(json.dumps(base_cfg))

            cfg["include_gravity"] = True
            cfg["include_hydrostatic"] = True
            cfg["include_crest_surcharge"] = bool(FIXED_LOAD_CASE["include_crest"])
            cfg["include_uplift"] = uplift_head_m > 0.0
            cfg["uplift"] = {
                "head_m": uplift_head_m,
                "pressure_factor": 1.0,
            }
            cfg["water"]["pressure_datum_z_m"] = float(FIXED_LOAD_CASE["datum_m"])
            cfg["water"]["downstream_head_m"] = 0.0
            if not FIXED_LOAD_CASE["include_crest"]:
                cfg["water"]["crest_head_m"] = 0.0
            cfg["support"]["base_spring"] = [k * float(envelope["base_scale"]) for k in base_springs_nominal]
            cfg["support"]["abutment_spring"] = [k * float(envelope["abutment_scale"]) for k in abutment_springs_nominal]
            cfg["results_directory"] = f"results_uplift_matrix/{case}"

            free_surface_z = float(FIXED_LOAD_CASE["datum_m"]) + upstream_head_m
            pressure_expr = make_pressure_expr(
                rho_water,
                gravity,
                free_surface_z,
                str(FIXED_LOAD_CASE["sign_mode"]),
                str(FIXED_LOAD_CASE["truncation_mode"]),
            )

            sif_text = build_sif(cfg)
            sif_text = rewrite_hydro_boundaries(sif_text, pressure_expr, str(FIXED_LOAD_CASE["boundary_mode"]))

            sif_path = SIF_DIR / f"dam_model_{case}.sif"
            sif_path.write_text(sif_text)

            max_tension_mpa: float | str = ""
            max_compression_mpa: float | str = ""
            summary_path = ""

            if run_solver:
                print(f"Running solver for {case}...")
                max_tension_mpa, max_compression_mpa, summary_path = run_solver_and_postprocess(
                    cfg,
                    sif_path,
                    resolved_solver,
                    elmer_home,
                    elmer_modules_path,
                    expected_tension_mpa,
                    expected_compression_mpa,
                )

            row: dict[str, float | str | bool] = {
                "case": case,
                "restraint_envelope": str(envelope["name"]),
                "base_scale": float(envelope["base_scale"]),
                "abutment_scale": float(envelope["abutment_scale"]),
                "include_uplift": uplift_head_m > 0.0,
                "uplift_head_m": uplift_head_m,
                "uplift_pressure_factor": 1.0,
                "sign_mode": str(FIXED_LOAD_CASE["sign_mode"]),
                "pressure_datum_z_m": float(FIXED_LOAD_CASE["datum_m"]),
                "boundary_mode": str(FIXED_LOAD_CASE["boundary_mode"]),
                "max_tension_mpa": max_tension_mpa,
                "max_compression_mpa": max_compression_mpa,
                "stress_summary_path": summary_path,
                "sif_path": str(sif_path.relative_to(ROOT)),
            }

            if run_solver and isinstance(max_tension_mpa, float) and isinstance(max_compression_mpa, float):
                row["abs_delta_tension_mpa"] = abs(max_tension_mpa - expected_tension_mpa)
                row["abs_delta_compression_mpa"] = abs(max_compression_mpa - expected_compression_mpa)
                row["combined_abs_delta_mpa"] = row["abs_delta_tension_mpa"] + row["abs_delta_compression_mpa"]

            rows.append(row)

    with CSV_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    JSON_PATH.write_text(json.dumps(rows, indent=2))

    print(f"Wrote {CSV_PATH}")
    print(f"Wrote {JSON_PATH}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Small uplift matrix on selected restraint envelopes.")
    parser.add_argument("--run-solver", action="store_true", help="Run ElmerSolver and stress post-processing for each case.")
    parser.add_argument("--solver-exe", default=None, help="Path to ElmerSolver executable.")
    parser.add_argument("--elmer-home", default=None, help="Optional ELMER_HOME value passed to solver runs.")
    parser.add_argument("--elmer-modules-path", default=None, help="Optional ELMER_MODULES_PATH value passed to solver runs.")
    parser.add_argument("--expected-tension-mpa", type=float, default=DEFAULT_EXPECTED_TENSION_MPA)
    parser.add_argument("--expected-compression-mpa", type=float, default=DEFAULT_EXPECTED_COMPRESSION_MPA)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run(
        run_solver=args.run_solver,
        solver_exe=args.solver_exe,
        elmer_home=args.elmer_home,
        elmer_modules_path=args.elmer_modules_path,
        expected_tension_mpa=args.expected_tension_mpa,
        expected_compression_mpa=args.expected_compression_mpa,
    )

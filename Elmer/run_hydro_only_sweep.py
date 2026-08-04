from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path

from build_calibration_sif import build_sif
from sweep_calibration_datum_head import ROOT, pick_solver_executable, run_solver_and_postprocess

SWEEP_DIR = ROOT / "hydro_sweep"
SIF_DIR = SWEEP_DIR / "sif_cases"
CSV_PATH = SWEEP_DIR / "hydro_only_sweep.csv"
JSON_PATH = SWEEP_DIR / "hydro_only_sweep.json"

DATUM_VALUES_M = [0.0, 2.0, 4.0, 6.0]
SIGN_MODES = ["negative", "positive"]
TRUNCATION_MODES = ["indicator", "max"]
BOUNDARY_MODES = ["correct_b2", "swapped_b3", "both_b2_b3"]

DEFAULT_EXPECTED_TENSION_MPA = 1.2
DEFAULT_EXPECTED_COMPRESSION_MPA = -3.33


def load_base_config() -> dict:
    return json.loads((ROOT / "calibration_case.json").read_text())


def case_name(sign_mode: str, datum_m: float, boundary_mode: str, truncation_mode: str) -> str:
    datum_text = f"{datum_m:.1f}".replace(".", "p").replace("-", "neg")
    return f"hydro_{sign_mode}_datum_{datum_text}m_{boundary_mode}_{truncation_mode}"


def make_pressure_expr(
    rho_water: float,
    gravity: float,
    free_surface_z_m: float,
    sign_mode: str,
    truncation_mode: str,
) -> str:
    if truncation_mode == "indicator":
        magnitude = f"{rho_water} * {gravity} * ({free_surface_z_m} - tx) * (tx < {free_surface_z_m})"
    elif truncation_mode == "max":
        # MATC-safe positive part: max(a, 0) = 0.5 * (a + abs(a)).
        magnitude = (
            f"{rho_water} * {gravity} * 0.5 * "
            f"(({free_surface_z_m} - tx) + abs({free_surface_z_m} - tx))"
        )
    else:
        raise ValueError(f"Unknown truncation mode: {truncation_mode}")

    if sign_mode == "negative":
        return f"-({magnitude})"
    if sign_mode == "positive":
        return magnitude
    raise ValueError(f"Unknown sign mode: {sign_mode}")


def rewrite_hydro_boundaries(sif_text: str, pressure_expr: str, boundary_mode: str) -> str:
    if boundary_mode == "correct_b2":
        b2_target = 2
        b3_target = 3
        b2_expr = pressure_expr
        b3_expr = "0.0"
    elif boundary_mode == "swapped_b3":
        b2_target = 3
        b3_target = 2
        b2_expr = pressure_expr
        b3_expr = "0.0"
    elif boundary_mode == "both_b2_b3":
        b2_target = 2
        b3_target = 3
        b2_expr = pressure_expr
        b3_expr = pressure_expr
    else:
        raise ValueError(f"Unknown boundary mode: {boundary_mode}")

    boundary_block = f'''Boundary Condition 2
  Name = "UpstreamHydrostaticPressure"
  Target Boundaries(1) = {b2_target}
  Normal Force = Variable Coordinate 3
    Real MATC "{b2_expr}"
End

Boundary Condition 3
  Name = "DownstreamTailwater"
  Target Boundaries(1) = {b3_target}
  Normal Force = Variable Coordinate 3
    Real MATC "{b3_expr}"
End'''

    pattern = re.compile(r'Boundary Condition 2\n[\s\S]*?End\n\nBoundary Condition 3\n[\s\S]*?End')
    if not pattern.search(sif_text):
        raise ValueError("Could not locate Boundary Condition 2/3 block in SIF text")
    return pattern.sub(boundary_block, sif_text, count=1)


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

    resolved_solver = None
    if run_solver:
        resolved_solver = pick_solver_executable(solver_exe)
        if resolved_solver is None:
            raise FileNotFoundError(
                "ElmerSolver executable not found. Pass --solver-exe or add ElmerSolver to PATH."
            )

    SWEEP_DIR.mkdir(parents=True, exist_ok=True)
    SIF_DIR.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, float | str]] = []

    for sign_mode in SIGN_MODES:
        for datum_m in DATUM_VALUES_M:
            for boundary_mode in BOUNDARY_MODES:
                for truncation_mode in TRUNCATION_MODES:
                    case = case_name(sign_mode, datum_m, boundary_mode, truncation_mode)

                    cfg = json.loads(json.dumps(base_cfg))
                    cfg["include_gravity"] = False
                    cfg["include_hydrostatic"] = True
                    cfg["include_crest_surcharge"] = False
                    cfg["water"]["pressure_datum_z_m"] = datum_m
                    cfg["water"]["downstream_head_m"] = 0.0
                    cfg["water"]["crest_head_m"] = 0.0
                    cfg["results_directory"] = f"results_hydro_sweep/{case}"

                    free_surface_z = datum_m + upstream_head_m
                    pressure_expr = make_pressure_expr(
                        rho_water,
                        gravity,
                        free_surface_z,
                        sign_mode,
                        truncation_mode,
                    )

                    sif_text = build_sif(cfg)
                    sif_text = rewrite_hydro_boundaries(sif_text, pressure_expr, boundary_mode)

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

                    row: dict[str, float | str] = {
                        "case": case,
                        "sign_mode": sign_mode,
                        "pressure_datum_z_m": datum_m,
                        "boundary_mode": boundary_mode,
                        "truncation_mode": truncation_mode,
                        "upstream_head_m": upstream_head_m,
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
    parser = argparse.ArgumentParser(description="Hydro-only sweep over sign, datum, boundary targeting, and truncation.")
    parser.add_argument(
        "--run-solver",
        action="store_true",
        help="Run ElmerSolver and stress post-processing for each case.",
    )
    parser.add_argument(
        "--solver-exe",
        default=None,
        help="Path to ElmerSolver executable. If omitted, common locations and PATH are checked.",
    )
    parser.add_argument(
        "--elmer-home",
        default=None,
        help="Optional ELMER_HOME value passed to solver runs.",
    )
    parser.add_argument(
        "--elmer-modules-path",
        default=None,
        help="Optional ELMER_MODULES_PATH value passed to solver runs.",
    )
    parser.add_argument(
        "--expected-tension-mpa",
        type=float,
        default=DEFAULT_EXPECTED_TENSION_MPA,
        help="Expected tension value recorded in per-case stress summaries.",
    )
    parser.add_argument(
        "--expected-compression-mpa",
        type=float,
        default=DEFAULT_EXPECTED_COMPRESSION_MPA,
        help="Expected compression value recorded in per-case stress summaries.",
    )
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

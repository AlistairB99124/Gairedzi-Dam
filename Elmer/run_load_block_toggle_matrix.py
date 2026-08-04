from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from build_calibration_sif import build_sif
from sweep_calibration_datum_head import (
    ROOT,
    pick_solver_executable,
    run_solver_and_postprocess,
)

TOGGLE_DIR = ROOT / "toggle_matrix"
SIF_DIR = TOGGLE_DIR / "sif_cases"
CSV_PATH = TOGGLE_DIR / "load_block_toggle_matrix.csv"
JSON_PATH = TOGGLE_DIR / "load_block_toggle_matrix.json"

DEFAULT_EXPECTED_TENSION_MPA = 1.2
DEFAULT_EXPECTED_COMPRESSION_MPA = -3.33


def load_base_config() -> dict:
    return json.loads((ROOT / "calibration_case.json").read_text())


def case_name(include_gravity: bool, include_hydrostatic: bool, include_crest: bool) -> str:
    return (
        f"g_{int(include_gravity)}"
        f"_h_{int(include_hydrostatic)}"
        f"_c_{int(include_crest)}"
    )


def build_cases() -> list[tuple[bool, bool, bool]]:
    cases: list[tuple[bool, bool, bool]] = []
    for include_gravity in (False, True):
        for include_hydrostatic in (False, True):
            for include_crest in (False, True):
                cases.append((include_gravity, include_hydrostatic, include_crest))

    # Keep outputs easy to read: increasing number of active load blocks.
    return sorted(cases, key=lambda item: (sum(int(x) for x in item), item))


def run(
    run_solver: bool,
    solver_exe: str | None,
    elmer_home: str | None,
    elmer_modules_path: str | None,
    expected_tension_mpa: float,
    expected_compression_mpa: float,
) -> None:
    base_cfg = load_base_config()

    resolved_solver = None
    if run_solver:
        resolved_solver = pick_solver_executable(solver_exe)
        if resolved_solver is None:
            raise FileNotFoundError(
                "ElmerSolver executable not found. Pass --solver-exe or add ElmerSolver to PATH."
            )

    TOGGLE_DIR.mkdir(parents=True, exist_ok=True)
    SIF_DIR.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, float | str | int | bool]] = []
    for include_gravity, include_hydrostatic, include_crest in build_cases():
        case = case_name(include_gravity, include_hydrostatic, include_crest)
        cfg = json.loads(json.dumps(base_cfg))
        cfg["include_gravity"] = include_gravity
        cfg["include_hydrostatic"] = include_hydrostatic
        cfg["include_crest_surcharge"] = include_crest
        cfg["results_directory"] = f"results_toggle/{case}"

        sif_text = build_sif(cfg)
        sif_path = SIF_DIR / f"dam_model_{case}.sif"
        sif_path.write_text(sif_text)

        max_tension_mpa: float | str = ""
        max_compression_mpa: float | str = ""
        stress_summary_path = ""
        if run_solver:
            print(f"Running solver for {case}...")
            max_tension_mpa, max_compression_mpa, stress_summary_path = run_solver_and_postprocess(
                cfg,
                sif_path,
                resolved_solver,
                elmer_home,
                elmer_modules_path,
                expected_tension_mpa,
                expected_compression_mpa,
            )

        row: dict[str, float | str | int | bool] = {
            "case": case,
            "include_gravity": include_gravity,
            "include_hydrostatic": include_hydrostatic,
            "include_crest_surcharge": include_crest,
            "active_load_blocks": int(include_gravity) + int(include_hydrostatic) + int(include_crest),
            "max_tension_mpa": max_tension_mpa,
            "max_compression_mpa": max_compression_mpa,
            "stress_summary_path": stress_summary_path,
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
    parser = argparse.ArgumentParser(description="Run gravity/hydro/crest load-block toggle matrix.")
    parser.add_argument(
        "--run-solver",
        action="store_true",
        help="Run ElmerSolver and stress post-processing for each toggle case.",
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

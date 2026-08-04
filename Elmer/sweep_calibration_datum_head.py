from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path
import shutil
import subprocess

from analyze_stress import analyze, latest_vtu_path
from build_calibration_sif import build_sif


ROOT = Path(__file__).resolve().parent
BASE_CONFIG_PATH = ROOT / "calibration_case.json"
SWEEP_DIR = ROOT / "calibration_sweeps"
SIF_DIR = SWEEP_DIR / "sif_cases"
CSV_PATH = SWEEP_DIR / "datum_head_sweep.csv"
JSON_PATH = SWEEP_DIR / "datum_head_sweep.json"
MESH_NODES_PATH = ROOT / "mesh" / "mesh.nodes"

# Adjust these lists to explore the load definition space.
DATUM_VALUES_M = [0.0, 2.0, 4.0, 6.0]
UPSTREAM_HEAD_VALUES_M = [25.0, 27.0, 29.0, 31.0]

DEFAULT_EXPECTED_TENSION_MPA = 1.2
DEFAULT_EXPECTED_COMPRESSION_MPA = -3.33


def load_base_config() -> dict:
    return json.loads(BASE_CONFIG_PATH.read_text())


def mesh_z_min() -> float:
    min_z = None
    with MESH_NODES_PATH.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            parts = stripped.split()
            if len(parts) < 5:
                continue
            z = float(parts[4])
            if min_z is None or z < min_z:
                min_z = z
    if min_z is None:
        raise ValueError(f"Could not read z values from {MESH_NODES_PATH}")
    return min_z


def case_name(datum_z_m: float, upstream_head_m: float) -> str:
    return (
        f"datum_{datum_z_m:.1f}m_head_{upstream_head_m:.1f}m"
        .replace(".", "p")
        .replace("-", "neg")
    )


def parse_float_list(value: str) -> list[float]:
    return [float(item.strip()) for item in value.split(",") if item.strip()]


def pick_solver_executable(cli_solver_exe: str | None) -> str | None:
    if cli_solver_exe:
        return cli_solver_exe

    candidates = [
        "/private/tmp/elmerfem-docs/build/fem/src/ElmerSolver",
        "/private/tmp/elmerfem-docs/bin/ElmerSolver",
        "/Users/alistairdavies/elmerfem/bin/ElmerSolver",
    ]
    for path in candidates:
        if Path(path).is_file() and os.access(path, os.X_OK):
            return path

    path_solver = shutil.which("ElmerSolver")
    if path_solver:
        return path_solver
    return None


def run_solver_and_postprocess(
    case_cfg: dict,
    case_sif_path: Path,
    solver_exe: str,
    elmer_home: str | None,
    elmer_modules_path: str | None,
    expected_tension_mpa: float,
    expected_compression_mpa: float,
) -> tuple[float, float, str]:
    case_results_dir = ROOT / case_cfg["results_directory"]
    if case_results_dir.exists():
        shutil.rmtree(case_results_dir)
    case_results_dir.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()

    resolved_elmer_home = elmer_home
    if not resolved_elmer_home:
        solver_path = Path(solver_exe).resolve()
        if solver_path.parent.name == "bin":
            resolved_elmer_home = str(solver_path.parent.parent)

    if resolved_elmer_home:
        env["ELMER_HOME"] = resolved_elmer_home

    resolved_modules_path = elmer_modules_path
    if not resolved_modules_path and resolved_elmer_home:
        candidate = Path(resolved_elmer_home) / "share" / "elmersolver" / "lib"
        if candidate.is_dir():
            resolved_modules_path = str(candidate)

    if resolved_modules_path:
        env["ELMER_MODULES_PATH"] = resolved_modules_path

    subprocess.run([solver_exe, str(case_sif_path.resolve())], cwd=ROOT, env=env, check=True)

    vtu_path = latest_vtu_path(case_results_dir)
    analyze(
        vtu_path,
        case_results_dir,
        float(case_cfg["material"]["youngs_modulus_pa"]),
        float(case_cfg["material"]["poisson_ratio"]),
        ROOT / "curved_dam_mesh.msh",
        ROOT / "load_cases.json",
        expected_tension_mpa,
        expected_compression_mpa,
    )
    summary = json.loads((case_results_dir / "stress_summary.json").read_text())
    return (
        summary["max_tensile_principal_stress_pa"]["value_pa"] / 1.0e6,
        summary["max_compressive_principal_stress_pa"]["value_pa"] / 1.0e6,
        str((case_results_dir / "stress_summary.json").relative_to(ROOT)),
    )


def run(
    datum_values_m: list[float],
    upstream_head_values_m: list[float],
    run_solver: bool,
    solver_exe: str | None,
    elmer_home: str | None,
    elmer_modules_path: str | None,
    expected_tension_mpa: float,
    expected_compression_mpa: float,
) -> None:
    config_base = load_base_config()
    rho_water = float(config_base["water"]["density_kg_m3"])
    g = float(config_base["water"]["gravity_m_s2"])
    z_min = mesh_z_min()

    resolved_solver = None
    if run_solver:
        resolved_solver = pick_solver_executable(solver_exe)
        if resolved_solver is None:
            raise FileNotFoundError(
                "ElmerSolver executable not found. Pass --solver-exe or add ElmerSolver to PATH."
            )

    SIF_DIR.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, float | str]] = []
    for datum in datum_values_m:
        for head in upstream_head_values_m:
            cfg = json.loads(json.dumps(config_base))
            cfg["water"]["pressure_datum_z_m"] = datum
            cfg["water"]["upstream_head_m"] = head
            cfg["water"]["target_peak_upstream_pressure_pa"] = rho_water * g * head
            cfg["results_directory"] = f"results_sweep/{case_name(datum, head)}"

            sif_text = build_sif(cfg)
            sif_path = SIF_DIR / f"dam_model_{case_name(datum, head)}.sif"
            sif_path.write_text(sif_text)

            free_surface_z = datum + head
            expected_peak_pa = rho_water * g * head
            realized_peak_at_mesh_min_pa = rho_water * g * max(free_surface_z - z_min, 0.0)

            max_tension_mpa = ""
            max_compression_mpa = ""
            summary_path = ""
            if run_solver:
                print(f"Running solver for {case_name(datum, head)}...")
                max_tension_mpa, max_compression_mpa, summary_path = run_solver_and_postprocess(
                    cfg,
                    sif_path,
                    resolved_solver,
                    elmer_home,
                    elmer_modules_path,
                    expected_tension_mpa,
                    expected_compression_mpa,
                )

            rows.append(
                {
                    "case": case_name(datum, head),
                    "pressure_datum_z_m": datum,
                    "upstream_head_m": head,
                    "free_surface_z_m": free_surface_z,
                    "mesh_min_z_m": z_min,
                    "expected_peak_pa": expected_peak_pa,
                    "realized_peak_at_mesh_min_pa": realized_peak_at_mesh_min_pa,
                    "realized_to_expected_ratio": (
                        realized_peak_at_mesh_min_pa / expected_peak_pa if expected_peak_pa > 0.0 else 0.0
                    ),
                    "max_tension_mpa": max_tension_mpa,
                    "max_compression_mpa": max_compression_mpa,
                    "stress_summary_path": summary_path,
                    "sif_path": str(sif_path.relative_to(ROOT)),
                }
            )

    SWEEP_DIR.mkdir(parents=True, exist_ok=True)

    with CSV_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    JSON_PATH.write_text(json.dumps(rows, indent=2))

    print(f"Wrote {CSV_PATH}")
    print(f"Wrote {JSON_PATH}")
    print(f"Generated {len(rows)} calibration SIF cases in {SIF_DIR}")
    if run_solver:
        print("Included ElmerSolver runs and stress metrics in sweep outputs.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sweep hydrostatic datum/head and optionally run ElmerSolver for each case.")
    parser.add_argument(
        "--datum-values",
        default=",".join(str(x) for x in DATUM_VALUES_M),
        help="Comma-separated datum z values in meters (default: 0,2,4,6)",
    )
    parser.add_argument(
        "--upstream-head-values",
        default=",".join(str(x) for x in UPSTREAM_HEAD_VALUES_M),
        help="Comma-separated upstream head values in meters (default: 25,27,29,31)",
    )
    parser.add_argument(
        "--run-solver",
        action="store_true",
        help="Run ElmerSolver and stress post-processing for each generated case.",
    )
    parser.add_argument(
        "--solver-exe",
        default=None,
        help="Path to ElmerSolver executable. If omitted, common locations and PATH are checked.",
    )
    parser.add_argument(
        "--elmer-home",
        default=os.environ.get("ELMER_HOME"),
        help="Optional ELMER_HOME value passed to solver runs.",
    )
    parser.add_argument(
        "--elmer-modules-path",
        default=os.environ.get("ELMER_MODULES_PATH"),
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
        parse_float_list(args.datum_values),
        parse_float_list(args.upstream_head_values),
        args.run_solver,
        args.solver_exe,
        args.elmer_home,
        args.elmer_modules_path,
        args.expected_tension_mpa,
        args.expected_compression_mpa,
    )

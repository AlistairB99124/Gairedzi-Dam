from __future__ import annotations

from pathlib import Path
import csv
import json
import os
import re
import shutil
import subprocess

from analyze_stress import analyze, latest_vtu_path


ROOT = Path(__file__).resolve().parent
ELMER_HOME = "/Users/alistairdavies/elmerfem"
ELMER_MODULES = "/Users/alistairdavies/elmerfem/share/elmersolver/lib"


def build_case_sif(template_text: str, case_name: str, downstream_head_m: float) -> str:
    case_results_dir = f'sweep_results/{case_name}'
    case_text = template_text
    case_text = re.sub(r'Results Directory "[^"]+"', f'Results Directory "{case_results_dir}"', case_text)
    case_text = re.sub(
        r'Real MATC "1000\.0 \* 9\.81 \* max\(2\.0 - tx, 0\.0\)"',
        f'Real MATC "1000.0 * 9.81 * max({downstream_head_m:.3f} - tx, 0.0)"',
        case_text,
        count=1,
    )
    return case_text


def run_case(case_name: str, downstream_head_m: float) -> dict[str, float]:
    template_path = ROOT / "dam_model.sif"
    case_sif_path = ROOT / f"dam_model_{case_name}.sif"
    sweep_root = ROOT / "sweep_results"
    case_output_dir = sweep_root / case_name

    if case_output_dir.exists():
        shutil.rmtree(case_output_dir)
    case_output_dir.mkdir(parents=True, exist_ok=True)

    case_sif_path.write_text(build_case_sif(template_path.read_text(), case_name, downstream_head_m))

    env = os.environ.copy()
    env["ELMER_HOME"] = ELMER_HOME
    env["ELMER_MODULES_PATH"] = ELMER_MODULES

    subprocess.run([
        f"{ELMER_HOME}/bin/ElmerSolver",
        case_sif_path.name,
    ], cwd=ROOT, env=env, check=True)

    vtu_path = latest_vtu_path(case_output_dir)
    analyze(
        vtu_path,
        case_output_dir,
        3.5e10,
        0.2,
        ROOT / "curved_dam_mesh.msh",
        ROOT / "load_cases.json",
        1.2,
        -3.33,
    )
    summary = json.loads((case_output_dir / "stress_summary.json").read_text())
    return {
        "case_name": case_name,
        "downstream_head_m": downstream_head_m,
        "max_tension_mpa": summary["max_tensile_principal_stress_pa"]["value_pa"] / 1.0e6,
        "max_compression_mpa": summary["max_compressive_principal_stress_pa"]["value_pa"] / 1.0e6,
    }


def main() -> None:
    sweep_cases = [
        ("tailwater_0p0m", 0.0),
        ("tailwater_2p0m", 2.0),
        ("tailwater_5p0m", 5.0),
        ("tailwater_10p0m", 10.0),
        ("tailwater_15p0m", 15.0),
        ("tailwater_20p0m", 20.0),
        ("tailwater_29p0m", 29.0),
    ]

    sweep_root = ROOT / "sweep_results"
    sweep_root.mkdir(parents=True, exist_ok=True)
    rows = []
    for case_name, downstream_head_m in sweep_cases:
        print(f"Running {case_name}...")
        rows.append(run_case(case_name, downstream_head_m))

    csv_path = sweep_root / "load_case_comparison.csv"
    with csv_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    summary_path = sweep_root / "load_case_comparison.json"
    summary_path.write_text(json.dumps(rows, indent=2))
    print(f"Wrote {csv_path}")
    print(f"Wrote {summary_path}")


if __name__ == "__main__":
    main()
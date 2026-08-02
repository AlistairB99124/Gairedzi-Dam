#!/usr/bin/env bash
set -Eeuo pipefail

SETUP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SETUP_DIR/.." && pwd)"
ELMER_DIR="$ROOT_DIR/Elmer"
LOG_DIR="$ROOT_DIR/results/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/run_$(date +%Y%m%d_%H%M%S).log"

exec > >(tee -a "$LOG_FILE") 2>&1

echo "============================================================"
echo "Gairedzi Dam one-click pipeline"
echo "Start time: $(date)"
echo "Log file: $LOG_FILE"
echo "============================================================"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "This launcher is configured for macOS."
  exit 1
fi

if [[ ! -d "$ELMER_DIR" ]]; then
  echo "Missing Elmer folder at: $ELMER_DIR"
  exit 1
fi

require_command() {
  local cmd="$1"
  local install_hint="$2"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "Missing command: $cmd"
    echo "$install_hint"
    exit 1
  fi
}

require_command python3 "Install Python 3 and retry."

echo "[1/6] Preparing Python environment..."
if [[ ! -d "$ROOT_DIR/.venv" ]]; then
  python3 -m venv "$ROOT_DIR/.venv"
fi

source "$ROOT_DIR/.venv/bin/activate"
python -m pip install --upgrade pip >/dev/null
python -m pip install -r "$ROOT_DIR/client_requirements.txt"

ELMERGRID_BIN=""
ELMERSOLVER_BIN=""
ELMER_HOME=""
ELMER_MODULES_PATH=""

detect_elmer() {
  if [[ -n "${ELMER_HOME:-}" ]] && [[ -x "$ELMER_HOME/bin/ElmerGrid" ]] && [[ -x "$ELMER_HOME/bin/ElmerSolver" ]]; then
    ELMERGRID_BIN="$ELMER_HOME/bin/ElmerGrid"
    ELMERSOLVER_BIN="$ELMER_HOME/bin/ElmerSolver"
    if [[ -d "$ELMER_HOME/share/elmersolver/lib" ]]; then
      ELMER_MODULES_PATH="$ELMER_HOME/share/elmersolver/lib"
    fi
    return 0
  fi

  local known_home="/Users/alistairdavies/elmerfem"
  if [[ -x "$known_home/bin/ElmerGrid" ]] && [[ -x "$known_home/bin/ElmerSolver" ]]; then
    ELMER_HOME="$known_home"
    ELMERGRID_BIN="$known_home/bin/ElmerGrid"
    ELMERSOLVER_BIN="$known_home/bin/ElmerSolver"
    if [[ -d "$known_home/share/elmersolver/lib" ]]; then
      ELMER_MODULES_PATH="$known_home/share/elmersolver/lib"
    fi
    return 0
  fi

  if command -v ElmerGrid >/dev/null 2>&1 && command -v ElmerSolver >/dev/null 2>&1; then
    ELMERGRID_BIN="$(command -v ElmerGrid)"
    ELMERSOLVER_BIN="$(command -v ElmerSolver)"
    return 0
  fi

  return 1
}

install_elmer_with_brew() {
  if ! command -v brew >/dev/null 2>&1; then
    echo "Homebrew is not installed. Installing Homebrew first..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  fi

  echo "Attempting to install Elmer via Homebrew..."
  if ! brew list --versions elmerfem >/dev/null 2>&1; then
    brew install elmerfem || brew install elmer
  fi
}

echo "[2/6] Detecting Elmer binaries..."
if ! detect_elmer; then
  echo "Elmer not found. Attempting automated install..."
  install_elmer_with_brew
  if ! detect_elmer; then
    echo "Unable to locate ElmerGrid/ElmerSolver after install attempt."
    echo "Please install Elmer manually and rerun this launcher."
    exit 1
  fi
fi

echo "Using ElmerGrid: $ELMERGRID_BIN"
echo "Using ElmerSolver: $ELMERSOLVER_BIN"

echo "[3/6] Rebuilding geometry and mesh from Data/..."
python "$ELMER_DIR/build_curved_dam_geometry.py"

echo "[4/6] Running ElmerGrid conversion..."
rm -rf "$ELMER_DIR/mesh" "$ELMER_DIR/results"
mkdir -p "$ELMER_DIR/mesh" "$ELMER_DIR/results"
(
  cd "$ELMER_DIR"
  "$ELMERGRID_BIN" 14 2 curved_dam_mesh.msh -autoclean -out mesh
)

echo "[5/6] Running ElmerSolver..."
(
  cd "$ELMER_DIR"
  if [[ -n "$ELMER_HOME" ]] && [[ -n "$ELMER_MODULES_PATH" ]]; then
    ELMER_HOME="$ELMER_HOME" ELMER_MODULES_PATH="$ELMER_MODULES_PATH" "$ELMERSOLVER_BIN" dam_model.sif
  else
    "$ELMERSOLVER_BIN" dam_model.sif
  fi
)

echo "[6/6] Running stress post-processing..."
python "$ELMER_DIR/analyze_stress.py"

REPORT_IMG="$ELMER_DIR/results/client_stress_report.png"
SUMMARY_JSON="$ELMER_DIR/results/stress_summary.json"

echo ""
echo "Pipeline complete."
echo "Summary file: $SUMMARY_JSON"
echo "Report image: $REPORT_IMG"
echo "Log file: $LOG_FILE"

if [[ -f "$REPORT_IMG" ]]; then
  open "$REPORT_IMG" || true
fi

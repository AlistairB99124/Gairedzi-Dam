#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "Launching Gairedzi dam pipeline..."
echo ""

"$ROOT_DIR/run_client_pipeline.sh"

echo ""
echo "Done. Press Enter to close this window."
read -r _

#!/bin/bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

CONDA="/opt/miniconda3/condabin/conda"
CONDA_BASE="$($CONDA info --base)"
source "${CONDA_BASE}/etc/profile.d/conda.sh"

conda activate s3_env

LOCKFILE="/tmp/noiseport_process_app.lock"
exec 200>"$LOCKFILE"

flock -n 200 || {
  echo "Pipeline already running. Exiting."
  exit 1
}

LOG_DIR="$(python - <<'PY'
from server_process_app.common.utils.utils import load_config
print(load_config()["paths"]["logs"])
PY
)"

mkdir -p "$LOG_DIR"

echo "=== PIPELINE START: $(date) ===" | tee -a "$LOG_DIR/pipeline.log"

python -m server_process_app.database.queries_server
python -m server_process_app.processing.peaksL50
python -m server_process_app.processing.alarms
python -m server_process_app.processing.visualization

echo "=== PIPELINE END: $(date) ===" | tee -a "$LOG_DIR/pipeline.log"
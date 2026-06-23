#!/bin/bash
set -euo pipefail


BASE="/home/aac/I+D/CODIGOS/NoisePort_server/[Automatize]_Pipeline"
LOG_DIR="$BASE/logs"
mkdir -p "$LOG_DIR"

#ruta a conda para que cron la encuentre
CONDA="/opt/miniconda3/condabin/conda"
CONDA_BASE="$($CONDA info --base)"


source "${CONDA_BASE}/etc/profile.d/conda.sh"
conda activate s3_env




# Lock para evitar solapamientos
LOCKFILE="/tmp/pipeline.lock"
exec 200>"$LOCKFILE"
flock -n 200 || { echo "Pipeline already running. Exiting."; exit 1; }

echo "=== PIPELINE START: $(date) ===" | tee -a "$LOG_DIR/pipeline.log"

# scripts y logs
scripts=(
#    "01_retrieve_hour.sh"
#    "02_move_audio.sh"
#    "03_exec_acoustic_params.sh"
#    "04_exec_inference.sh"
    "05_exec_queries.sh"
    "06_exec_peaks.sh"
    "07_exec_alarms.sh"
    "08_exec_visualizations.sh"
)

for script in "${scripts[@]}"; do

    echo ">>> Running $script ..." | tee -a "$LOG_DIR/$script.log"
    bash "$BASE/$script" >> "$LOG_DIR/$script.log" 2>&1
    echo ">>> Finished $script at $(date)" | tee -a "$LOG_DIR/$script.log"

done

echo "=== PIPELINE END: $(date) ===" | tee -a "$LOG_DIR/pipeline.log"

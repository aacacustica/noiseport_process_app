#!/bin/bash

set -e

REPO_ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"

cd "$REPO_ROOT"

source ~/miniconda3/etc/profile.d/conda.sh

conda activate s3_env

python -m server_process_app.database.queries_server

python -m server_process_app.processing.peak_detection_server_L50

python -m server_process_app.processing.alarms

python -m server_process_app.processing.visualizations
#!/usr/bin/env bash
# Run the H3a notebook headless with papermill, in the background (nohup).
#
#   scripts/run_h3a.sh [RUN_LEVEL] [SAMPLE_FRAC] [REPORT_DIR] [OUTPUT_NOTEBOOK]
#
# Defaults: level 1, full data, reports/h3a, notebooks/H3a-rendered.ipynb.
# Smoke test: scripts/run_h3a.sh 1 0.1 reports/h3a_smoke reports/h3a_smoke/H3a-smoke.ipynb
# Follow progress: tail -f <REPORT_DIR>/run.log ; timings: <REPORT_DIR>/timings.csv
set -euo pipefail
cd "$(dirname "$0")/.."

LEVEL="${1:-1}"
FRAC="${2:-1.0}"
REPORT_DIR="${3:-reports/h3a}"
OUT_NB="${4:-notebooks/H3a-rendered.ipynb}"
FOREGROUND="${H3A_FOREGROUND:-0}"

mkdir -p "$REPORT_DIR"
CMD=(uv run papermill notebooks/H3a.ipynb "$OUT_NB"
     -p RUN_LEVEL "$LEVEL" -p SAMPLE_FRAC "$FRAC" -p REPORT_DIR "$REPORT_DIR"
     --cwd . --log-output --progress-bar)

if [[ "$FOREGROUND" == "1" ]]; then
  "${CMD[@]}" 2>&1 | tee -a "$REPORT_DIR/run.log"
else
  nohup "${CMD[@]}" >>"$REPORT_DIR/run.log" 2>&1 &
  echo "started PID $! (log: $REPORT_DIR/run.log)"
fi

#!/usr/bin/env bash
# Full H3a run: level 1, then level 2 (fits from level 1 come from cache), detached from the
# terminal session (setsid + nohup), so closing the shell or the agent session does not stop it.
#
#   scripts/run_h3a_full.sh [REPORT_DIR]
#
# Progress: tail -f <REPORT_DIR>/run.log ; timings: <REPORT_DIR>/timings.csv
# A final line "H3A DONE ..." or "H3A FAILED ..." is appended to run.log.
set -euo pipefail
cd "$(dirname "$0")/.."
REPORT_DIR="${1:-reports/h3a}"
mkdir -p "$REPORT_DIR"
setsid nohup bash -c '
  R="$1"
  echo "H3A START $(date -Is)" >>"$R/run.log"
  if H3A_FOREGROUND=1 timeout 3h scripts/run_h3a.sh 1 1.0 "$R" notebooks/H3a-rendered.ipynb \
       >/dev/null 2>&1 &&
     H3A_FOREGROUND=1 timeout 2h scripts/run_h3a.sh 2 1.0 "$R" notebooks/H3a-rendered.ipynb \
       >/dev/null 2>&1; then
    echo "H3A DONE $(date -Is)" >>"$R/run.log"
  else
    echo "H3A FAILED $(date -Is)" >>"$R/run.log"
  fi
' _ "$REPORT_DIR" </dev/null >/dev/null 2>&1 &
echo "started detached PID $! (log: $REPORT_DIR/run.log)"

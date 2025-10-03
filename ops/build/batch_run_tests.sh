#!/usr/bin/env bash
# Continuously run a focused pytest subset and write coverage JSON to a known path.
# Use: ./scripts/batch_run_tests.sh [max_iterations]

set -euo pipefail
cd "$(dirname "$0")/.."
PYTHONPATH=. export PYTHONPATH
FOCUSED_EXPR='ble_link or ble_gateway or ble_utils or core_types or verify_discovery or logging_setup or addon_config'
OUT=coverage-explicit.json
MAX=${1:-0}
COUNT=0

while true; do
  ((COUNT++))
  echo "[batch_run_tests] Iteration $COUNT"
  if [ "$MAX" -ne 0 ] && [ "$COUNT" -gt "$MAX" ]; then
    echo "Reached max iterations ($MAX). Exiting."
    exit 0
  fi

  # Run pytest and write a deterministic coverage JSON. Keep -q to reduce noise.
  PYTHONPATH=. pytest -q --maxfail=1 --disable-warnings -k "$FOCUSED_EXPR" --cov=./addon --cov-report=json:"$OUT" || {
    echo "[batch_run_tests] Test run failed. Sleeping 2s before retrying..."
    sleep 2
    continue
  }

  echo "[batch_run_tests] Test run completed, coverage written to $OUT"
  # Short pause to avoid hammering CPU if everything is passing.
  sleep 1
done

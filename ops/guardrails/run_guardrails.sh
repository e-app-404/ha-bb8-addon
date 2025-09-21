#!/usr/bin/env bash
set -euo pipefail

# Run all guardrail checks in ops/guardrails
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SCRIPTS_DIR="$ROOT_DIR/guardrails"

echo "Running guardrails in $SCRIPTS_DIR"
fail=0
for s in "$SCRIPTS_DIR"/*.sh; do
  # Skip the runner itself to avoid accidental self-invocation/recursion
  base=$(basename "$s")
  if [ "$base" = "run_guardrails.sh" ]; then
    continue
  fi
  [ -x "$s" ] || continue
  echo
  echo "-> Running $base"
  if ! "$s"; then
    echo "Guardrail failed: $base" >&2
    fail=1
    break
  fi
done

if [ "$fail" -ne 0 ]; then
  echo "One or more guardrails failed" >&2
  exit 2
fi

echo
echo "All guardrails passed"
exit 0

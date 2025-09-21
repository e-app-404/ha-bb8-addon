#!/usr/bin/env bash
set -euo pipefail

# Guardrail: ensure there are no Python files under a top-level tools/ directory.
# Exit non-zero if any .py files are present under tools/ at repo root.

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
TARGET="$ROOT_DIR/tools"

if [ -d "$TARGET" ]; then
  # find python files (excluding hidden files)
  mapfile -t pyfiles < <(find "$TARGET" -type f -name '*.py' -not -path '*/.venv/*' -print)
  if [ ${#pyfiles[@]} -gt 0 ]; then
    echo "ERROR: Forbidden top-level tools/ directory contains Python files at $TARGET"
    echo "Per ADR-0019, code should live in addon/tools or ops/tools, not at repo root."
    printf "Offending files:\n"
    for f in "${pyfiles[@]}"; do echo " - $f"; done
    exit 2
  fi
fi

echo "OK: no top-level tools/ Python files present"
exit 0

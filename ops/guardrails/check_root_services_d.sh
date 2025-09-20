#!/usr/bin/env bash
set -euo pipefail

# Guardrail: ensure there is no services.d/ directory at the repository root.
# Exit with non-zero status if any files exist under services.d/ at repo root.

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
TARGET="$ROOT_DIR/services.d"

if [ -d "$TARGET" ]; then
  # check for any files (not just empty dirs)
  # ignore .gitkeep if present
  shopt -s nullglob dotglob 2>/dev/null || true
  files=("$TARGET"/*)
  if [ ${#files[@]} -gt 0 ]; then
    echo "ERROR: Forbidden top-level services.d/ found at $TARGET"
    echo "All runtime services must live under addon/services.d/ as per ADR-0019."
    echo "Remove or relocate files under services.d/ to addon/services.d/."
    exit 2
  fi
fi

echo "OK: no top-level services.d/ present"
exit 0

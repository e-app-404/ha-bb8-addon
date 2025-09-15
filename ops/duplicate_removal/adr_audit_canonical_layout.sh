#!/usr/bin/env bash
set -euo pipefail


# Use repo root for all paths, robust from any location
REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_ROOT"

echo "=== Step 3: ADR audit for canonical module layout ==="

ADR_DIR="$REPO_ROOT/docs/ADR"
mkdir -p "$ADR_DIR"

# Find an ADR that declares "addon/ is the code root" & "no root-level bb8_core"
match=$(grep -RIlE 'canonical.+addon/|code\s*root.+addon/|no\s+root-?level\s+bb8_core' "$ADR_DIR" || true)
if [ -z "${match}" ]; then
  ADR="$ADR_DIR/ADR-0012-canonical-module-layout-and-workspace-shape.md"
  cat > "$ADR" <<'MD'
# ADR-0012: Canonical module layout & workspace shape

**Status:** Accepted  
**Date:** $(date +%Y-%m-%d)

## Decision

- The **only** canonical Python module tree is `addon/bb8_core/`.
- Root-level `bb8_core/` is **forbidden**. Any occurrence is considered drift and must be removed.
- All imports must use `addon.bb8_core.*`. Bare `bb8_core.*` imports are disallowed.
- Tests, tools, and services live under `addon/{tests,tools,services.d}`.

## Rationale

- Single code root eliminates duplication, import ambiguity, and CI drift.
- Matches packaging, runtime, and CI expectations.

## Consequences

- CI shape guard enforces this ADR.
- Pre-commit hook rejects commits that reintroduce root-level `bb8_core/`.

MD
  (cd "$REPO_ROOT" && git add "$ADR")
  (cd "$REPO_ROOT" && git commit -m "docs(ADR): add ADR-0012 canonical module layout & workspace shape")
else
  echo "ADR already present: $match"
fi

echo "=== ADR check complete ==="

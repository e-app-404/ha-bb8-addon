#!/usr/bin/env bash
set -euo pipefail

# Threshold: 50MB
thresh=$((50*1024*1024))
mode="local"; [ "${CI:-}" = "true" ] && mode="ci"

fail(){ printf '%s\n' "$*" >&2; exit 1; }

# Detect tracked symlinks (120 mode entries)
if git ls-files -s | awk '$1 ~ /^120/ {print $4}' | grep -q .; then
  echo "ERROR: symlinks tracked in Git:" >&2
  git ls-files -s | awk '$1 ~ /^120/ {print $4}' >&2
  exit 2
fi

# Build diff command for local vs CI
DIFF_CMD=()
if [ "$mode" = "local" ]; then
  DIFF_CMD=(git diff --cached --name-only --diff-filter=AM -z)
else
  if [ -n "${GITHUB_BASE_REF:-}" ]; then
    base_ref="$GITHUB_BASE_REF"
    git fetch origin "$base_ref" --depth=1 || true
    DIFF_CMD=(git diff --name-only "origin/${base_ref}...HEAD" -z)
  else
    git fetch origin main --depth=1 || true
    DIFF_CMD=(git diff --name-only origin/main...HEAD -z)
  fi
fi

# Run DIFF_CMD once and capture (NUL-safe). Fallback to full tracked file scan if empty/fails.
tmpf="$(mktemp)"; trap 'rm -f "$tmpf"' EXIT
if ! "${DIFF_CMD[@]}" >"$tmpf" 2>/dev/null || [ ! -s "$tmpf" ]; then
  : > "$tmpf"
  git ls-files -z >> "$tmpf"
fi

ok=1
while IFS= read -r -d '' f; do
  [ -f "$f" ] || continue
  sz=$(wc -c < "$f")
  if [ "$sz" -gt "$thresh" ]; then
    printf 'ERROR: Large file (>50MB): %s (%d bytes)\n' "$f" "$sz" >&2
    ok=0
  fi
done < "$tmpf"

[ "$ok" -eq 1 ] && echo "OK: size/symlink guard passed" || exit 3

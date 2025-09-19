#!/usr/bin/env bash
set -euo pipefail
# Move addon/.ruff_cache into _backups safely before a push
# Usage: move_ruff_cache_before_push.sh [--force]

FORCE=0
if [ "${1-}" = "--force" ]; then FORCE=1; fi

RUNTIME_CACHE="addon/.ruff_cache"
DEST_DIR="_backups/ruff_cache_backups"

if [ ! -d "$RUNTIME_CACHE" ]; then
  echo "No addon/.ruff_cache present; nothing to move"
  exit 0
fi

mkdir -p "$DEST_DIR"
TS=$(date -u +%Y%m%dT%H%M%SZ)
TARGET="$DEST_DIR/.ruff_cache_${TS}"

if [ -e "$TARGET" ]; then
  if [ "$FORCE" -eq 1 ]; then
    rm -rf "$TARGET"
  else
    echo "Target $TARGET already exists; use --force to overwrite" >&2
    exit 1
  fi
fi

echo "Moving $RUNTIME_CACHE -> $TARGET"
mv "$RUNTIME_CACHE" "$TARGET"
echo "Moved; run 'ls -ld $TARGET' to inspect"

exit 0

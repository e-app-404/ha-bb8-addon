#!/usr/bin/env bash
set -euo pipefail

# make_workspace_tarball.sh - Create a clean workspace tarball for HA-BB8
# Usage: ./scripts/make_workspace_tarball.sh <output_tarball>
# Example: ./scripts/make_workspace_tarball.sh HA-BB8_clean_$(date +%Y%m%d_%H%M%S).tar.gz

WS="/Users/evertappels/Projects/HA-BB8"
TARBALL_NAME="${1:-HA-BB8_clean_$(date +%Y%m%d_%H%M%S).tar.gz}"
OUT="$WS/docs/tarballs/$TARBALL_NAME"

EXCLUDES=(
  --exclude='.venv*'
  --exclude='__pycache__'
  --exclude='*.pyc'
  --exclude='.DS_Store'
  --exclude='.vscode'
  --exclude='.pytest_cache'
  --exclude='.mypy_cache'
  --exclude='.ruff_cache'
  --exclude='docs/tarballs/'
  --exclude='reports/patches/'
  --exclude='reports/qa_*/'
  --exclude='reports/stp4_*/'
  --exclude='reports/stp4_evidence/'
  --exclude='reports/addon/'
  --exclude='addon/.venv*'
  --exclude='addon/__pycache__'
  --exclude='addon/.pytest_cache'
  --exclude='addon/.mypy_cache'
  --exclude='addon/.ruff_cache'
  --exclude='addon/.vscode'
  --exclude='addon/.DS_Store'
  --exclude='_backup*/'
)

cd "$WS"

# Create tarball
tar czf "$OUT" "${EXCLUDES[@]}" .

# Output tarball size
SIZE=$(du -h "$OUT" | awk '{print $1}')

# Count files included (list files in tarball, exclude directories)
FILE_COUNT=$(tar -tzf "$OUT" | grep -v '/$' | wc -l)

# Compute sha256
SHA256=$(shasum -a 256 "$OUT" | awk '{print $1}')

echo "[ok] Workspace tarball created: $OUT"
echo "[info] Size: $SIZE"
echo "[info] Files included: $FILE_COUNT"
echo "[info] SHA256: $SHA256"

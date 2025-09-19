#!/usr/bin/env bash
set -euo pipefail
export LC_ALL=C

# Helper: move *.bak files into the repository _backups dir and log the operations.
# By default this runs only once every 24h; pass --force to override.

FORCE=0
while [ "$#" -gt 0 ]; do
  case "$1" in
    --force) FORCE=1; shift ;;
    --help) echo "Usage: $0 [--force]"; exit 0 ;;
    *) echo "Unknown arg: $1"; exit 2 ;;
  esac
done

# Determine project root (assume ops/utils/* location)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." >/dev/null 2>&1 && pwd)"

BACKUP_ROOT="$PROJECT_ROOT/_backups"
REPORTS_DIR="$PROJECT_ROOT/reports/move_backups"
mkdir -p "$BACKUP_ROOT" "$REPORTS_DIR"

LAST_RUN_FILE="$BACKUP_ROOT/.last_move_run"
NOW_TS=$(date +%s)
NOW_READABLE=$(date +"%Y-%m-%d %H:%M:%S")

if [ -f "$LAST_RUN_FILE" ] && [ "$FORCE" -eq 0 ]; then
  LAST_TS=$(cat "$LAST_RUN_FILE" 2>/dev/null || echo 0)
  DIFF=$((NOW_TS - LAST_TS))
  if [ "$DIFF" -lt $((24*3600)) ]; then
    echo "Last run $DIFF seconds ago (<24h). Use --force to override." >&2
    exit 0
  fi
fi

RUNSTAMP=$(date +"%Y%m%d_%H%M%S")
LOGFILE="$REPORTS_DIR/run_${RUNSTAMP}.log"
echo "move_backups run: $NOW_READABLE" > "$LOGFILE"
echo "project_root: $PROJECT_ROOT" >> "$LOGFILE"
echo "backup_root: $BACKUP_ROOT" >> "$LOGFILE"
echo "search: looking for *.bak files (excluding _backups, .git, reports)" >> "$LOGFILE"

# find .bak files excluding _backups, .git and reports directories
cd "$PROJECT_ROOT"
IFS=$'\n'
set -f
FILES=( $(find . -type f -name '*.bak' \
  -not -path './_backups/*' -not -path './.git/*' -not -path './reports/*' 2>/dev/null) )
set +f
IFS=$' \t\n'

if [ ${#FILES[@]} -eq 0 ]; then
  echo "no .bak files found" >> "$LOGFILE"
  echo "$NOW_TS" > "$LAST_RUN_FILE"
  echo "No files moved. Wrote last-run marker." >> "$LOGFILE"
  exit 0
fi

echo "found ${#FILES[@]} .bak files" >> "$LOGFILE"

for f in "${FILES[@]}"; do
  # normalize path, strip leading ./
  orig="${f#./}"
  src="$PROJECT_ROOT/$orig"
  # target path under _backups preserving directory structure
  dest="$BACKUP_ROOT/$orig"
  dest_dir="$(dirname "$dest")"
  mkdir -p "$dest_dir"

  # record file metadata
  size=$(wc -c < "$src" 2>/dev/null || echo 0)
  sha=$(shasum -a 256 "$src" 2>/dev/null | awk '{print $1}' || echo "-")

  echo "[$NOW_READABLE] MOVING: $src -> $dest (size=${size}, sha256=${sha})" | tee -a "$LOGFILE"
  mv "$src" "$dest"
  if [ $? -eq 0 ]; then
    echo "  moved: $orig -> ${dest#$PROJECT_ROOT/}" >> "$LOGFILE"
  else
    echo "  ERROR moving $src" >> "$LOGFILE"
  fi
done

echo "$NOW_TS" > "$LAST_RUN_FILE"
echo "Completed at $(date +"%Y-%m-%d %H:%M:%S")" >> "$LOGFILE"
echo "Moved ${#FILES[@]} files. Log: $LOGFILE"

exit 0

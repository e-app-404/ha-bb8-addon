#!/usr/bin/env bash
set -euo pipefail

# Configurable thresholds
LOC_THRESHOLD="${LOC_THRESHOLD:-2000}"
FILES_THRESHOLD="${FILES_THRESHOLD:-80}"
STATE_FILE="${STATE_FILE:-_backups/.snapshot_state.json}"
TARBALL_DIR="${TARBALL_DIR:-_backups}"    # keep ignored by git
UNTRACKED_DIR="${UNTRACKED_DIR:-_backups/inventory}"
DRY_RUN=0
FORCE=0

usage() {
  cat <<USAGE
snapshot_policy.sh [--dry-run]
  Evaluates change since last snapshot mark and, if thresholds met, creates:
    * Tracked-tree tarball:   ${TARBALL_DIR}/wtree_<TS>.tgz
    * Untracked inventory:    ${UNTRACKED_DIR}/untracked_<TS>.txt
Env:
  LOC_THRESHOLD        default=${LOC_THRESHOLD}
  FILES_THRESHOLD      default=${FILES_THRESHOLD}
  STATE_FILE           default=${STATE_FILE}
  TARBALL_DIR          default=${TARBALL_DIR}
  UNTRACKED_DIR        default=${UNTRACKED_DIR}
USAGE
}

# Args
for arg in "${@:-}"; do
  case "$arg" in
    --dry-run) DRY_RUN=1 ;;
    --force) FORCE=1 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown arg: $arg" >&2; usage; exit 2 ;;
  esac
done

mkdir -p "$(dirname "$STATE_FILE")" "$TARBALL_DIR" "$UNTRACKED_DIR"

# Last mark
LAST=""
if [ -f "$STATE_FILE" ]; then
  LAST="$(jq -r '.last_commit // empty' "$STATE_FILE" 2>/dev/null || true)"
fi
if [ -z "${LAST:-}" ]; then
  # First commit as baseline if no state
  FIRST="$(git rev-list --max-parents=0 HEAD)"
  RANGE="${FIRST}..HEAD"
else
  RANGE="${LAST}..HEAD"
fi

# Compute metrics
# numstat: <added>\t<deleted>\t<path>
ADDED=0; DELETED=0; CHANGED=0
while IFS=$'\t' read -r a d p; do
  # skip blank lines
  [ -z "${p:-}" ] && continue
  case "$a" in ''|'-') a=0 ;; esac
  case "$d" in ''|'-') d=0 ;; esac
  ADDED=$((ADDED + a))
  DELETED=$((DELETED + d))
  CHANGED=$((CHANGED + 1))
done < <(git diff --numstat "$RANGE" || true)

LOC_CHANGED=$((ADDED + DELETED))

# Decision
NEEDS_SNAPSHOT=0
[ "$LOC_CHANGED" -ge "$LOC_THRESHOLD" ] && NEEDS_SNAPSHOT=1
[ "$CHANGED"    -ge "$FILES_THRESHOLD" ] && NEEDS_SNAPSHOT=1
[ ! -f "$STATE_FILE" ] && NEEDS_SNAPSHOT=1
[ "$FORCE" -eq 1 ] && NEEDS_SNAPSHOT=1

TS="$(date +%Y%m%d_%H%M%S)"

# Always emit a dry summary to stdout
printf '{"dry_run":%s,"needs_snapshot":%s,"range":"%s","loc_changed":%s,"files_changed":%s,"loc_threshold":%s,"files_threshold":%s}\n' \
  "$DRY_RUN" "$NEEDS_SNAPSHOT" "$RANGE" "$LOC_CHANGED" "$CHANGED" "$LOC_THRESHOLD" "$FILES_THRESHOLD"

if [ "$DRY_RUN" -eq 1 ]; then
  exit 0
fi

if [ "$NEEDS_SNAPSHOT" -eq 0 ]; then
  # Update state (noop but refresh metrics)
  git rev-parse HEAD >/dev/null
  jq -n --arg commit "$(git rev-parse HEAD)" \
        --argjson loc "$LOC_CHANGED" \
        --argjson files "$CHANGED" \
        '{last_commit:$commit,last_loc_changed:$loc,last_files_changed:$files,ts:"'$TS'"}' > "$STATE_FILE"
  exit 0
fi

# Create tracked-only tarball
TARBALL="${TARBALL_DIR}/wtree_${TS}.tgz"
git ls-files -z | tar --null -czf "$TARBALL" --files-from - || {
  echo "ERROR: tarball creation failed" >&2
  exit 1
}

# Write untracked inventory
git ls-files --others --exclude-standard | sort > "${UNTRACKED_DIR}/untracked_${TS}.txt"

# Update state to current HEAD
jq -n --arg commit "$(git rev-parse HEAD)" \
      --argjson loc "$LOC_CHANGED" \
      --argjson files "$CHANGED" \
      '{last_commit:$commit,last_loc_changed:$loc,last_files_changed:$files,ts:"'$TS'"}' > "$STATE_FILE"

echo "SNAPSHOT_OK tarball=${TARBALL} untracked=${UNTRACKED_DIR}/untracked_${TS}.txt"

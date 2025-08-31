#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

ADDON="addon"
TS="$(date -u +%Y%m%d_%H%M%SZ)"
MIGDIR="$ADDON/_migrated_conflicts_${TS}"
DRY="${DRY_RUN:-1}"      # default dry-run
APPLY="${APPLY:-0}"      # set APPLY=1 to execute changes

# Filters (do not migrate caches/artifacts)
EXCLUDES=(
  --exclude='__pycache__' --exclude='*.pyc' --exclude='.pytest_cache'
  --exclude='.ruff_cache' --exclude='.mypy_cache' --exclude='coverage.json'
  --exclude='pytest-report.xml' --exclude='.DS_Store'
)
dirs=(bb8_core app tests tools services.d)
files=(config.yaml Dockerfile run.sh requirements.txt requirements-dev.txt \
       requirements.in requirements-dev.in pyproject.toml mypy.ini ruff.toml \
       apparmor.txt VERSION)

plan() { echo "PLAN: $*"; }
act()  { echo "DO:   $*"; eval "$@"; }
ensure_dir() { [ -d "$1" ] || { [ "$APPLY" = "1" ] && mkdir -p "$1" || true; } }

# Sanity: addon exists
[ -d "$ADDON" ] || { echo "FATAL: addon/ missing"; exit 2; }

echo "== Consolidation plan (DRY_RUN=${DRY}, APPLY=${APPLY}) =="

# 1) Directories
for d in "${dirs[@]}"; do
  root_d="$d"
  addon_d="$ADDON/$d"
  if [ -d "$root_d" ] && [ -d "$addon_d" ]; then
    # Compare trees and list differences
    plan "diff -qr ${EXCLUDES[*]} '$root_d' '$addon_d'"
    diff_out="$(diff -qr "${EXCLUDES[@]}" "$root_d" "$addon_d" || true)"
    if [ -n "$diff_out" ]; then
      echo "$diff_out" | while read -r line; do
        case "$line" in
          "Only in "*": "*) 
            # only-in-root → move into addon
            src_dir="${line#Only in }"
            src_dir="${src_dir%%:*}"
            src_name="${line##*: }"
            src_path="$src_dir/$src_name"
            rel="${src_path#./}"
            dest="$ADDON/$rel"
            plan "git mv '$rel' '$dest'"
            [ "$APPLY" = "1" ] && git mv "$rel" "$dest" || true
            ;;
          "Files "*" and "*" differ")
            # conflict → keep addon, park root copy
            left="${line#Files }"; left="${left%% and *}"
            right="${line##* and }"; right="${right%% differ}"
            rel="${left#./}"
            park="$MIGDIR/$rel.root"
            plan "CONFLICT: keep '$right', park '$left' → '$park'"
            if [ "$APPLY" = "1" ]; then
              ensure_dir "$(dirname "$park")"
              cp -p "$left" "$park"
            fi
            ;;
        esac
      done
    fi
  elif [ -d "$root_d" ] && [ ! -d "$addon_d" ]; then
    # Entire dir leaked at root → move under addon
    plan "git mv '$root_d' '$addon_d'"
    [ "$APPLY" = "1" ] && git mv "$root_d" "$addon_d" || true
  fi
done

# 2) Files at repo root
for f in "${files[@]}"; do
  root_f="$f"
  addon_f="$ADDON/$f"
  if [ -f "$root_f" ] && [ -f "$addon_f" ]; then
    if ! cmp -s "$root_f" "$addon_f"; then
      park="$MIGDIR/$f.root"
      plan "CONFLICT: keep '$addon_f', park '$root_f' → '$park'"
      if [ "$APPLY" = "1" ]; then
        ensure_dir "$(dirname "$park")"
        cp -p "$root_f" "$park"
        # keep addon version as canonical
        git rm --cached "$root_f" >/dev/null 2>&1 || true
        rm -f "$root_f"
      fi
    else
      # identical → remove duplicate at root
      plan "DEDUP: remove duplicate '$root_f'"
      if [ "$APPLY" = "1" ]; then
        git rm --cached "$root_f" >/dev/null 2>&1 || true
        rm -f "$root_f"
      fi
    fi
  elif [ -f "$root_f" ] && [ ! -f "$addon_f" ]; then
    dest_dir="$(dirname "$addon_f")"
    plan "git mv '$root_f' '$addon_f'"
    if [ "$APPLY" = "1" ]; then
      ensure_dir "$dest_dir"
      git mv "$root_f" "$addon_f"
    fi
  fi
done

# 3) Ensure no bad COPY lines in Dockerfile
DF="$ADDON/Dockerfile"
if [ -f "$DF" ]; then
  if grep -qE 'COPY[[:space:]]+addon/' "$DF"; then
    plan "Fix Dockerfile: remove COPY lines referencing 'addon/...'"
    if [ "$APPLY" = "1" ]; then
      tmp="$(mktemp)"
      awk '!/COPY[[:space:]]+addon\//{print}' "$DF" > "$tmp"
      mv "$tmp" "$DF"
      git add "$DF"
    fi
  fi
fi

# 4) Stage and commit
echo "== Staging =="
[ "$APPLY" = "1" ] && git add -A || true

echo "== Summary tokens =="
echo "TOKEN: CONSOLIDATION_PLAN_OK"
[ "$APPLY" = "1" ] && echo "TOKEN: CONSOLIDATION_APPLIED:$TS" || true
[ -d "$MIGDIR" ] && echo "TOKEN: MIGRATED_CONFLICTS_DIR:$MIGDIR" || true

echo "== Next =="
echo "DRY_RUN done. Re-run with: APPLY=1 DRY_RUN=0 bash $0"

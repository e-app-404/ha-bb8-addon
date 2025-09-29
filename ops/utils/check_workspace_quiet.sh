#!/usr/bin/env sh
# ops/check_workspace_quiet.sh
#
# Read-only workspace hygiene check.
# Prints "OK" and exits 0 when no forbidden shapes are found.
# Prints one "VIOLATION ..." line per issue and exits 1 otherwise.
#
# Policy (aligned with ADR-0018/0024):
# - No legacy backup suffixes (*.bak, *.perlbak, *_backup, *_restore) in the working tree.
# - No editor detritus (*~, *.swp, *.tmp, *.temp).
# - No bundles/tarballs outside allowed zones (tarballs/, _backups/).
# - No stray manifests at repo root (manifest_*.txt, tree_*.txt, report.json, restore_commands.sh).
# - No portability-hostile filenames (colon ":").
# - Optional: if inside a Git repo, flag any *tracked* files matching the above.
#
# Usage:
#   sh ops/check_workspace_quiet.sh            # checks "."
#   sh ops/check_workspace_quiet.sh /path/to/repo
#
# BusyBox/ash compatible. No writes, no staging.

set -eu
LC_ALL=C

ROOT="${1:-.}"
# Normalize ROOT to a path without trailing slash for consistent comparisons.
case "$ROOT" in
  */) ROOT="${ROOT%/}";;
esac

viols=0
say() { printf '%s\n' "$*"; }
emit() { viols=$((viols+1)); printf 'VIOLATION %-22s %s%s\n' "$1" "$2" "${3:+  # $3}"; }

# Helpers to build a prune expression for find (portable)
is_prune_dir() {
  case "$1" in
    "$ROOT/.git"|"$ROOT/.git/"*|\
    "$ROOT/_backups"|"$ROOT/_backups/"*|\
    "$ROOT/tarballs"|"$ROOT/tarballs/"*|\
    "$ROOT/node_modules"|"$ROOT/node_modules/"*|\
    "$ROOT/.venv"|"$ROOT/.venv/"*)
      return 0;;
    *) return 1;;
  esac
}

# Scan filesystem for legacy backup suffixes & editor detritus
# Exclude .git/, _backups/, tarballs/, node_modules/, .venv/
find "$ROOT" -type f 2>/dev/null | while IFS= read -r p; do
  # prune dirs by path prefix (portable)
  case "$p" in
    */.git/*|*/_backups/*|*/tarballs/*|*/node_modules/*|*/.venv/*) continue;;
  esac
  fn=${p##*/}

  # Legacy backups
  case "$fn" in
    *.perlbak|*_backup|*_backup.*|*_restore|*_restore.*|*.bak|*.bak.*)
      emit "legacy_backup" "$p" "rename to *.bk.<UTC> or relocate under _backups/"
      continue;;
  esac

  # Editor/temp detritus
  case "$fn" in
    *~|*.swp|*.tmp|*.temp)
      emit "editor_temp" "$p" "remove or move under .trash/"
      continue;;
  esac

  # Bundles/tarballs outside allowed zones
  case "$fn" in
    *.tar.gz|*.tgz|*.zip|*.bundle)
      emit "bundle_outside_allowed" "$p" "keep binaries under tarballs/ or _backups/ (ignored)"
      continue;;
  esac

  # Portability: filename with colon
  case "$fn" in
    *:*)
      emit "portable_name" "$p" "avoid ':' in filenames"
      continue;;
  esac
done

# Stray manifests at repo ROOT (exactly at ROOT, not subdirs)
if [ -d "$ROOT" ]; then
  # Only consider files that are directly under ROOT
  # (not under _backups/inventory or staging)
  for f in "$ROOT"/manifest_*.txt "$ROOT"/tree_*.txt "$ROOT"/report.json "$ROOT"/restore_commands.sh; do
    [ -f "$f" ] || continue
    emit "stray_manifest_root" "$f" "move to _backups/inventory/ or staging dir"
  done
fi

# Legacy root directories enforcement (ADR-0025/0019)
# These should not exist or be non-empty after migration to addon/
for legacy_dir in bb8_core services.d tests app tools; do
  legacy_path="$ROOT/$legacy_dir"
  if [ -d "$legacy_path" ]; then
    # Check if directory has content (not just empty or containing only .gitkeep)
    if [ -n "$(find "$legacy_path" -mindepth 1 -maxdepth 1 ! -name '.gitkeep' -print | head -1)" ]; then
      emit "legacy_root_content" "$legacy_path" "migrate content to addon/$legacy_dir/ per ADR-0025"
    fi
  fi
done

# Optional Git-index check: if in a Git repo, flag *tracked* junk
if [ -d "$ROOT/.git" ] && command -v git >/dev/null 2>&1; then
  # List tracked files; flag those that match forbidden shapes
  # (We intentionally do not prune here; tracked junk anywhere is a violation.)
  git -C "$ROOT" ls-files -z 2>/dev/null | tr '\0' '\n' | while IFS= read -r t; do
    case "$t" in
      *.perlbak|*_backup|*_backup.*|*_restore|*_restore.*|*.bak|*.bak.*|*~|*.swp|*.tmp|*.temp|*.tar.gz|*.tgz|*.zip|*.bundle|*:*)
        emit "tracked_junk" "$ROOT/$t" "remove from index (git rm --cached) / rename / relocate"
        ;;
    esac
  done
fi

# Result
if [ "$viols" -eq 0 ]; then
  say "OK"
  exit 0
else
  say "TOTAL_VIOLATIONS $viols"
  exit 1
fi

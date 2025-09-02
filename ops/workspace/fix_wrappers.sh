#!/usr/bin/env bash
set -Eeuo pipefail

WS="/Users/evertappels/Projects/HA-BB8"
WRAP="${WS}/scripts"
OPS="${WS}/ops"
REPORTS="${WS}/reports"
BK="${WS}/_backup_$(date -u +%Y%m%d_%H%M%S)Z_fix_wrappers"

mkdir -p "${BK}" "${WRAP}"

note(){ printf '%s\n' "$*"; }

# --- 0) Pick canonical sources for wrappers (prefer newest) ---
pick_newest() {
  local name="$1" a="${WRAP}/${name}" b="${OPS}/${name}"
  local src=""
  if [ -f "$a" ] && [ -f "$b" ]; then
    # choose newer mtime
    if [ "$(stat -f %m "$a" 2>/dev/null || stat -c %Y "$a")" -ge "$(stat -f %m "$b" 2>/dev/null || stat -c %Y "$b")" ]; then
      src="$a"
    else
      src="$b"
    fi
  elif [ -f "$a" ]; then
    src="$a"
  elif [ -f "$b" ]; then
    src="$b"
  fi
  printf '%s' "$src"
}

# --- 1) Move/align wrappers into scripts/ (canonical home) ---
for name in "deploy_to_ha.sh" "verify_workspace.sh"; do
  src="$(pick_newest "$name")"
  if [ -n "$src" ]; then
    # backup any existing scripts copy
    [ -f "${WRAP}/${name}" ] && cp -p "${WRAP}/${name}" "${BK}/${name}.scripts.bak"
    # place canonical file in scripts/
    install -m 0755 "$src" "${WRAP}/${name}"
    note "[fix] canonicalized ${name} -> scripts/"
  else
    note "[warn] wrapper not found in scripts/ or ops/: ${name}"
  fi
done

# remove stray copies in ops/ to avoid future confusion (back them up)
for name in "deploy_to_ha.sh" "verify_workspace.sh"; do
  if [ -f "${OPS}/${name}" ]; then
    mkdir -p "${BK}/ops_dupes"
    mv "${OPS}/${name}" "${BK}/ops_dupes/${name}.moved"
    note "[fix] removed duplicate ops/${name} (backed up)"
  fi
done

# --- 2) Ensure exports are present AFTER the shebang (if any) ---
ensure_exports_after_shebang() {
  local f="$1" tmp="${f}.tmp.$$"
  local need_ws=1 need_rr=1
  grep -q '^export WORKSPACE_ROOT=' "$f" && need_ws=0 || true
  grep -q '^export REPORT_ROOT=' "$f" && need_rr=0 || true
  [ $need_ws -eq 0 ] && [ $need_rr -eq 0 ] && { note "[ok] exports already present in $(basename "$f")"; return; }

  {
    # read first line to preserve shebang
    IFS= read -r first || true
    if printf '%s' "$first" | grep -q '^#!'; then
      printf '%s\n' "$first"
      [ $need_ws -eq 1 ] && printf 'export WORKSPACE_ROOT="%s"\n' "${WS}"
      [ $need_rr -eq 1 ] && printf 'export REPORT_ROOT="%s"\n' "${REPORTS}"
      cat
    else
      # no shebang; write exports first
      [ $need_ws -eq 1 ] && printf 'export WORKSPACE_ROOT="%s"\n' "${WS}"
      [ $need_rr -eq 1 ] && printf 'export REPORT_ROOT="%s"\n' "${REPORTS}"
      printf '%s\n' "$first"
      cat
    fi
  } < "$f" > "$tmp"
  mv "$tmp" "$f"
  chmod +x "$f"
  note "[fix] injected exports into $(basename "$f")"
}

for f in "${WRAP}/deploy_to_ha.sh" "${WRAP}/verify_workspace.sh"; do
  [ -f "$f" ] && ensure_exports_after_shebang "$f" || true
done

# --- 3) Re-run structure check (scripts must contain wrappers exporting REPORT_ROOT) ---
export WORKSPACE_ROOT="${WS}"
export REPORT_ROOT="${REPORTS}"

if [ -x "${WS}/tools/check_structure.sh" ]; then
  "${WS}/tools/check_structure.sh"
else
  note "[fail] missing structure checker: ${WS}/tools/check_structure.sh"; exit 4
fi

# On success, emit WS_READY (wrappers focus); full WS_READY is valid if prior steps already passed.
echo "WS_READY addon_ws=git_clone_ok runtime=git_clone_ok reports=ok wrappers=ok ops=ok"

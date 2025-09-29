#!/usr/bin/env bash
# HA-BB8: compile • test • coverage • gate • bleep • ADR check (deterministic output)

# Hardened deterministic health check script
set -eo pipefail
# Portable repository detection
if git rev-parse --show-toplevel >/dev/null 2>&1; then
    REPO="$(git rev-parse --show-toplevel)"
else
    REPO="$(pwd)"
fi
cd "$REPO" || { echo "repo path not found: $REPO"; exit 1; }
export RPROMPT=""

# --- Info: git presence (doesn't stop anything) ---
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "git: OK on branch $(git rev-parse --abbrev-ref HEAD)"
else
  echo "git: ⚠️  not a repo – tests/bleep still run."
fi

# --- Python env ---
python3 -m venv .venv 2>/dev/null || true
. .venv/bin/activate
python -m pip install -U pip >/dev/null
python -m pip install -U pytest pytest-cov pytest-asyncio pyyaml >/dev/null

# --- Ensure Makefile has a compile target + correct bleep invocation (safe/no-op if absent) ---
python - <<'PY' || true
from pathlib import Path
import re
mf = Path("Makefile")
if not mf.exists():
    print("NOTE: Makefile missing; skipping Makefile patch.")
else:
    t = mf.read_text(encoding="utf-8")
    if "\ncompile:" not in t:
        t += "\n\n.PHONY: compile\ncompile:\n\t@python -m compileall -q .\n"
    t = re.sub(r'(?m)^\s*python\s+tools/bleep_run\.py\s*$', 'python -m addon.tools.bleep_run', t)
    t = re.sub(r'(?ms)(^bleep:\s*\n(?:\t[^\n]*\n)?)',
               lambda m: m.group(1).replace('python tools/bleep_run.py','python -m addon.tools.bleep_run'), t)
    mf.write_text(t, encoding="utf-8")
    print("Makefile patched (compile target ensured; bleep normalized).")
PY

# --- Clean up known stray prints in test_facade.py (safe if file missing) ---
python - <<'PY' || true
from pathlib import Path
p = Path("addon/tests/test_facade.py")
if not p.exists():
    print("NOTE: addon/tests/test_facade.py not found; skip cleanup.")
else:
    lines = p.read_text(encoding="utf-8").splitlines()
    out = []
    for ln in lines:
        s = ln.strip()
        if s.startswith(('print("inst_calls:', "print('inst_calls:")): continue
        if s.startswith(('print("static_calls:', "print('static_calls:")): continue
        out.append(ln)
    p.write_text("\n".join(out) + "\n", encoding="utf-8")
    print("test_facade.py: debug prints removed.")
PY

# --- Compile everything (portable) ---
python -m compileall -q .

# --- Tests + coverage (do not abort the script if tests fail) ---
# env toggles to avoid accidental network usage in tests
export ALLOW_NETWORK_TESTS=0
pytest -q -rA --disable-warnings --maxfail=1 \
  --cov=addon --cov=addon/bb8_core \
  --cov-report=term-missing --cov-report=xml:coverage.xml || true

# --- Coverage gate (only if both script and report exist) ---
if [ -f addon/tools/coverage_gate.py ] && [ -f coverage.xml ]; then
  python addon/tools/coverage_gate.py coverage.xml || true
else
  echo "NOTE: coverage_gate or coverage.xml missing; skipped."
fi

# --- Bleep proof-of-life (prefer Makefile target; fallback to module) ---
( make bleep || python -m addon.tools.bleep_run ) || true

# --- Evidence: show newest bleep log & quick ADR presence check ---
echo "Latest bleep log:"
ls -1t reports/bleep_run_*.log 2>/dev/null | head -n 1 | xargs -I{} sh -c 'echo {}; sed -n "1,20p" "{}"' || echo "no bleep logs yet"
echo
echo "ADR (0001..0019) presence check:"

missing=0
for n in $(seq 1 19); do
  num=$(printf "%04d" "$n")
  matches=(docs/ADR/ADR-$num*.md)
  if [ ! -e "${matches[0]}" ]; then
    echo "MISSING: ADR-$num"
    missing=1
  fi
done
[ $missing -eq 0 ] && echo "ADR-0001..ADR-0019: OK"

# --- Done ---
echo "RUN COMPLETE."
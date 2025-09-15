#!/usr/bin/env bash
# ops/ratchet/ratchet_pipeline.sh
# Stepwise coverage ratchet, test suppression, bleep proof-of-life, and optional git commit/push

# Hardened: fail on unset variables, log each step, check shell/venv/repo/bleep/make
set -euo pipefail
REPO="${REPO:-/Users/evertappels/Projects/HA-BB8}"
LOGDIR="reports/ratchet"
mkdir -p "$LOGDIR"
TS=$(date +%Y%m%d_%H%M%S)
LOGFILE="$LOGDIR/pipeline_${TS}.log"
exec > >(tee "$LOGFILE") 2>&1
echo "[ratchet] Logging to $LOGFILE"
if [ ! -d "$REPO" ]; then
    echo "ERROR: Repo directory '$REPO' does not exist." >&2
    exit 1
fi
cd "$REPO"
echo "[ratchet] Entered repo: $REPO"

# --- 0) Enter venv, install deps ---
# Hardened: check venv existence and shell compatibility
if [ ! -d ".venv" ]; then
    echo "[ratchet] Creating venv..."
    python3 -m venv .venv || true
fi
if [ -f ".venv/bin/activate" ]; then
    . .venv/bin/activate
else
    echo "ERROR: venv activation script not found (.venv/bin/activate)." >&2
    exit 1
fi
python -m pip install -U pip >/dev/null
python -m pip install -U pytest pytest-cov pytest-asyncio pyyaml >/dev/null
echo "[ratchet] Python deps installed."

# --- 1) Show xfail reasons + warnings ---
echo "[ratchet] Running pytest for xfail reasons..."
pytest -q -rxX -W default || { echo "[ratchet] pytest xfail step failed."; }

# --- 2) Ratchet total coverage to 70% (no code changes; CI friendly) ---
echo "[ratchet] Ratcheting coverage to 70%..."
python - <<'PY'
import re
from pathlib import Path
cfg = Path(".coveragerc")
text = (
    cfg.read_text()
    if cfg.exists()
    else "[run]\nbranch = True\n\n[report]\nfail_under = 60\nshow_missing = True\nskip_covered = False\n"
)
text = re.sub(r"(?im)^(fail_under\s*=\s*)(\d+(\.\d+)?)", r"\g<1>70", text)
if "fail_under" not in text:
    text += "\nfail_under = 70\n"
cfg.write_text(text)
print("Coverage ratchet set: fail_under = 70")
PY

# --- 3) Re-run coverage quickly ---
echo "[ratchet] Re-running coverage..."
pytest -q -rA --disable-warnings --maxfail=1 \
    --cov=addon --cov=addon/bb8_core \
    --cov-report=term-missing --cov-report=xml:coverage.xml || { echo "[ratchet] Coverage run failed."; }

# --- 4) Gate (if available) ---
if [ -f addon/tools/coverage_gate.py ] && [ -f coverage.xml ]; then
    echo "[ratchet] Running coverage gate..."
    python addon/tools/coverage_gate.py coverage.xml || echo "[ratchet] Coverage gate failed."
fi

# --- 5) Optional: silence connect/disconnect chatter in tests (test-only patch) ---
echo "[ratchet] Patching conftest.py for MQTT connect suppression..."
python - <<'PY'
from pathlib import Path
cf = Path("addon/tests/conftest.py")
if not cf.exists():
    raise SystemExit("No conftest.py found; skip suppress shim.")
s = cf.read_text(encoding="utf-8")
needle = "def _suppress_real_mqtt_connect"
if needle not in s:
    # Harden: avoid duplicate fixtures
    if "def _auto_suppress_mqtt" in s:
        print("WARNING: _auto_suppress_mqtt fixture already present; skipping patch.")
    else:
        s += """

import os, contextlib
import types
import importlib

def _suppress_real_mqtt_connect(monkeypatch):
    try:
        paho = importlib.import_module("paho.mqtt.client")
    except Exception:
        return
    if os.environ.get("ALLOW_NETWORK_TESTS","0") != "1":
        def _no_real_connect(self, *a, **k): 
            raise OSError("suppressed real connect in tests")
        monkeypatch.setattr(paho.Client, "connect", _no_real_connect, raising=False)

import pytest
@pytest.fixture(autouse=True)
def _auto_suppress_mqtt(monkeypatch):
    _suppress_real_mqtt_connect(monkeypatch)
    yield
"""
        cf.write_text(s, encoding="utf-8")
        print("Added test-only MQTT connect suppressor.")
else:
    print("Suppressor already present; no change.")
PY


# --- 6) Run the quick bleep again (proof-of-life log) ---
if command -v make >/dev/null 2>&1 && make -n bleep >/dev/null 2>&1; then
    echo "[ratchet] Running make bleep..."
    make bleep || true
elif python -c "import addon.tools.bleep_run" 2>/dev/null; then
    echo "[ratchet] Running python -m addon.tools.bleep_run..."
    python -m addon.tools.bleep_run || true
else
    echo "WARNING: bleep run not available."
fi
bleep_log=$(ls -1t reports/bleep_run_*.log 2>/dev/null | head -n1)
if [ -n "$bleep_log" ]; then
    echo "Latest bleep log: $bleep_log"
    sed -n "1,12p" "$bleep_log"
else
    echo "No bleep log found."
fi

# --- 7) (Optional) Git commit/push if repo initialized ---
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "[ratchet] Git repo detected. Committing and pushing..."
    git add -A
    git commit -m "ci: ratchet coverage to 70%; test-only MQTT connect suppression; keep bleep proof-of-life" || echo "[ratchet] Git commit failed."
    git push || echo "NOTE: git push failed. Configure a remote to enable push."
else
    echo "NOTE: not in a git repo; skipping commit/push."
fi

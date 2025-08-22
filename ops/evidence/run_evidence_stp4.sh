#!/usr/bin/env bash
set -e

OUTDIR="$1"
VENV_PATH="/Users/evertappels/Projects/HABIBI-8/local.mac.beep_boop_bb8/.venv_new"
ACTIVATE="$VENV_PATH/bin/activate"

# 1. Detect if a virtual environment is active
if [ -z "$VIRTUAL_ENV" ]; then
    echo "[LOG] No virtual environment is active."
    if [ ! -f "$ACTIVATE" ]; then
        echo "[ERROR] Virtual environment not found at $ACTIVATE."
        echo "Please create one with: python3 -m venv $VENV_PATH"
        exit 1
    fi
    echo "[LOG] Activating virtual environment at $ACTIVATE."
    source "$ACTIVATE"
else
    echo "[LOG] Virtual environment already active: $VIRTUAL_ENV"
fi

# 2. Check for missing dependencies
MISSING=""
for pkg in paho.mqtt bleak; do
    python3 -c "import $pkg" 2>/dev/null || MISSING="$MISSING $pkg"
done

if [ -n "$MISSING" ]; then
    echo "[WARNING] Missing dependencies:$MISSING"
    echo "[LOG] Installing missing dependencies from requirements.txt..."
    pip install -r requirements.txt
fi

# 3. Run the evidence collection script
PYTHONPATH=. python3 ops/evidence/collect_stp4.py --timeout 3.0 --out "$OUTDIR"

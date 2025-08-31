#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ADDON_DIR="${REPO_ROOT}/addon"
VENV_DIR="${ADDON_DIR}/.venv_evidence"

# pick python3
if command -v python3 >/dev/null 2>&1; then PY=python3
elif command -v python >/dev/null 2>&1; then PY=python
else
  echo "[bootstrap] No python interpreter found." >&2; exit 127
fi

echo "[bootstrap] creating venv at ${VENV_DIR}"
$PY -m venv "${VENV_DIR}"
"${VENV_DIR}/bin/pip" install --upgrade pip

REQ="${ADDON_DIR}/ops/evidence/requirements.txt"
if [[ -f "${REQ}" ]]; then
  echo "[bootstrap] installing requirements from ${REQ}"
  "${VENV_DIR}/bin/pip" install -r "${REQ}"
else
  echo "[bootstrap] requirements.txt not found, installing minimal deps"
  "${VENV_DIR}/bin/pip" install paho-mqtt==2.1.0 PyYAML>=6.0.1
fi

echo "[bootstrap] ready. python=${VENV_DIR}/bin/python"
exit 0

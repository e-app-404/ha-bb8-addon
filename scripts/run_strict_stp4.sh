#!/usr/bin/env bash
export WORKSPACE_ROOT="/Users/evertappels/Projects/HA-BB8"
export REPORT_ROOT="/Users/evertappels/Projects/HA-BB8/reports"

set -euo pipefail

PROJ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ADDON="${PROJ}/addon"

# Load env (fail if missing)
ENV_FILE="${PROJ}/.evidence.env"
if [[ ! -f "${ENV_FILE}" ]]; then
  echo "[run] Missing ${ENV_FILE}. Create it from the template in the PR." >&2
  exit 2
fi
set -a
# shellcheck disable=SC1090
source "${ENV_FILE}"
set +a

# Validate required vars; default port
: "${MQTT_HOST:?[run] MQTT_HOST is required in .evidence.env}"
MQTT_PORT="${MQTT_PORT:-1883}"
# username compatibility
export MQTT_USERNAME="${MQTT_USERNAME:-${MQTT_USER:-}}"
export MQTT_USER="${MQTT_USER:-${MQTT_USERNAME:-}}"
export MQTT_PASSWORD="${MQTT_PASSWORD:-}"
if ! [[ "${MQTT_PORT}" =~ ^[0-9]+$ ]]; then
  echo "[run] MQTT_PORT must be an integer; got '${MQTT_PORT}'" >&2
  exit 3
fi

# Bootstrap evidence venv
bash "${PROJ}/scripts/bootstrap_evidence_env.sh"

"${ADDON}/.venv_evidence/bin/python" "${PROJ}/scripts/check_bridge_broker.py" || {
  echo "[run] BB-8 bridge not visible on ${MQTT_HOST}:${MQTT_PORT} (no '${MQTT_BASE}/status'='online')." >&2
  echo "[run] Fix: Either (A) point .evidence.env to the broker the add-on uses, or (B) reconfigure the add-on to this broker, then try again." >&2
  exit 20
}

# Smoke check for MQTT handler attachment
"${ADDON}/.venv_evidence/bin/python" "${PROJ}/scripts/smoke_handlers.py" || {
  echo "[run] MQTT handlers not active on ${MQTT_HOST}:${MQTT_PORT} (no diag/echo_stop seen). Fix handler attach in mqtt_dispatcher.on_connect." >&2
  exit 21
}

# Run evidence from addon
cd "${ADDON}"
make evidence-stp4 || true

# Summarize latest report
LATEST="$(ls -td ../reports/stp4_* 2>/dev/null | head -n1 || true)"
MANIFEST="${LATEST}/evidence_manifest.json"
TRACE_JSONL="${LATEST}/ha_mqtt_trace_snapshot.jsonl"
TRACE_JSON="${LATEST}/ha_mqtt_trace_snapshot.json"

echo "== latest report: ${LATEST} =="
if [[ -f "${MANIFEST}" ]]; then
  jq -r '. as $m | "roundtrip=\($m.roundtrip) schema=\($m.schema) timeouts_sec=\($m.timeouts_sec) generated_at=\($m.generated_at)"' "${MANIFEST}"
else
  echo "manifest not found"
fi

TF=""
[[ -f "${TRACE_JSONL}" ]] && TF="${TRACE_JSONL}"
[[ -z "${TF}" && -f "${TRACE_JSON}" ]] && TF="${TRACE_JSON}"
if [[ -n "${TF}" ]]; then
  echo "== trace file: ${TF} =="
  grep -F '"source":"facade"' "${TF}" >/dev/null && echo "WARN: facade echoes found" || echo "OK: no facade echoes"
  { grep -F '"source":"device"' "${TF}" | head; } || true
  { grep -E '"r":[0-9]+,"g":[0-9]+,"b":[0-9]+' "${TF}" | head; } || true
fi

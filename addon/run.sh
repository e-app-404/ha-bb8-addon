#!/usr/bin/env bash
set -Eeuo pipefail

# Strategos instrumentation (Gate A)
log_ts() { printf "[%s] %s\n" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*"; }

log_ts "ECHO: run.sh starting (instrumented)"
# Masked env preview (no secrets)
( env | grep -E '^(MQTT_HOST|MQTT_PORT|MQTT_BASE|REQUIRE_DEVICE_ECHO|PYTHONPATH)=' | sed -E 's/=.+/=\[MASKED\]/' ) || true

# Python sanity checks (do not fail add-on if unavailable; we log and continue)
python3 - << 'PY' || true
import sys
try:
    import paho.mqtt.client as m
    v = getattr(m, '__version__', 'unknown')
    print(f"PYENV_OK PAHO={v}")
except Exception as e:
    print(f"PYENV_FAIL {type(e).__name__}: {e}")
PY

MODE="${MODE:-echo}"
if [[ "$MODE" == "sentinel" ]]; then
  log_ts "ECHO: SENTINEL START (60s)"
  exec python3 - << 'PY'
import time
print("SENTINEL START", flush=True)
time.sleep(60)
PY
fi

# Default: echo foreground process
log_ts "ECHO: launching bb8_core.echo_responder (foreground exec)"
exec python3 -m bb8_core.echo_responder

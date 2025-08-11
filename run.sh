


#!/usr/bin/with-contenv bash
set -euo pipefail
export PYTHONUNBUFFERED=1
export PYTHONPATH=/app:${PYTHONPATH:-}
cd /app

log(){ echo "$(date -Is) [BB-8] $*"; }



pwd  # debug: print current working directory
log "Starting bridge controller…"

# Start the Python service
exec /opt/venv/bin/python3 -m bb8_core.bridge_controller

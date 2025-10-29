#!/usr/bin/env bash
set -Eeuo pipefail

# Supervisor-only, MQTT-only B5 runner (Acceptance-compliant)
# - Restarts add-on via HA Core API (no SSH/docker exec)
# - Runs MQTT echo health and persistence checks from workstation
# - Writes artifacts under reports/checkpoints/BB8-FUNC/supervisor_<TS>/

ROOT_DIR="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT_DIR"

# Optional: auto-source .evidence.env if present (contains secrets; not committed)
if [[ -f .evidence.env ]]; then
  set -a; source .evidence.env; set +a
fi

TS="${TS:-$(date -u +%Y%m%dT%H%M%SZ)}"
OUT_DIR="reports/checkpoints/BB8-FUNC/supervisor_${TS}"
mkdir -p "$OUT_DIR"

ADDON_SLUG="${ADDON_SLUG:-local_beep_boop_bb8}"
HA_URL="${HA_URL:-}"
HA_TOKEN="${HA_TOKEN:-${HA_LONG_LIVED_ACCESS_TOKEN:-}}"
MQTT_HOST="${MQTT_HOST:-}"; MQTT_PORT="${MQTT_PORT:-1883}"
MQTT_USER="${MQTT_USER:-}"; MQTT_PASSWORD="${MQTT_PASSWORD:-}"
MQTT_BASE="${MQTT_BASE:-bb8}"

err() { echo "ERROR: $*" >&2; }
need() { local v="$1"; local n="$2"; [[ -n "$v" ]] || { err "$n is required"; exit 2; }; }

need "$HA_URL" "HA_URL"; need "$HA_TOKEN" "HA_TOKEN";
need "$MQTT_HOST" "MQTT_HOST"; need "$MQTT_USER" "MQTT_USER"; need "$MQTT_PASSWORD" "MQTT_PASSWORD";

echo "[INFO] Restarting add-on via HA API: $ADDON_SLUG" | tee "$OUT_DIR/addon_restart.log"
set +e
HTTP_CODE=$(curl -sS -o "$OUT_DIR/addon_restart.response.json" -w "%{http_code}" \
  -H "Authorization: Bearer $HA_TOKEN" -H "Content-Type: application/json" \
  -X POST -d "{\"addon\":\"$ADDON_SLUG\"}" "$HA_URL/api/services/hassio/addon_restart")
set -e
echo "http_code=$HTTP_CODE" | tee -a "$OUT_DIR/addon_restart.log"
sleep 2

# MQTT echo health (captures summary JSON on stdout)
ECHO_SUM="$OUT_DIR/echo_summary.json"
python3 reports/checkpoints/INT-HA-CONTROL/mqtt_health_echo_test.py \
  --host "$MQTT_HOST" --port "$MQTT_PORT" \
  --user "$MQTT_USER" --password "$MQTT_PASSWORD" \
  --base "$MQTT_BASE" --sla-ms 1000 \
  --out "$OUT_DIR/mqtt_roundtrip.log" | tee "$ECHO_SUM"

# G1/G2: supervised MQTT-only probes with CID correlation
PY_G="$OUT_DIR/gates_probe.py"
cat > "$PY_G" <<'PY'
import os, json, time
from datetime import datetime, timezone
import paho.mqtt.client as mqtt

HOST=os.environ['MQTT_HOST']; PORT=int(os.environ.get('MQTT_PORT','1883'))
USER=os.environ.get('MQTT_USER'); PASS=os.environ.get('MQTT_PASSWORD')
BASE=os.environ.get('MQTT_BASE','bb8')
OUT=os.environ['OUT_DIR']
CID=os.environ.get('CID', f"g2-{int(time.time())}")

tele={'connected':None}
acks={}

def now():
  return datetime.now(timezone.utc).isoformat()

def on_message(c,u,m):
  s=m.payload.decode('utf-8','ignore')
  if m.topic == f"{BASE}/status/telemetry":
    try:
      d=json.loads(s); tele['connected']=d.get('connected', tele['connected'])
    except: pass
  if m.topic.startswith(f"{BASE}/ack/"):
    try:
      d=json.loads(s); cid=d.get('cid'); ok=bool(d.get('ok'))
      if cid: acks[cid]={'ok':ok,'raw':d,'ts':time.time()}
    except: pass

cl=mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
if USER and PASS:
  cl.username_pw_set(USER,PASS)
cl.on_message=on_message
cl.connect(HOST, PORT, 30)
cl.subscribe([ (f"{BASE}/ack/#",0), (f"{BASE}/status/telemetry",0) ])
cl.loop_start()

def pub(topic, payload):
  cl.publish(topic, json.dumps(payload), qos=0, retain=False)

# Pre-wait for telemetry up to 30s (G1)
t0=time.time()
while time.time()-t0<30 and tele['connected'] is None:
  time.sleep(0.05)
open(os.path.join(OUT,'telemetry.json'), 'w').write(json.dumps(tele))
open(os.path.join(OUT,'G1.status'),'w').write('ACCEPT\n' if tele['connected'] is not None else 'REWORK\n')

# G2: diag_scan and actuate_probe
c1=f"{CID}-c1"; c2=f"{CID}-c2"
open(os.path.join(OUT,'cid.txt'),'w').write(CID+"\n")

# Subscribe window per command
def wait(cid, to=14.0):
  t=time.time()
  while time.time()-t<to:
    if cid in acks: return acks[cid]
    time.sleep(0.02)
  return None

pub(f"{BASE}/cmd/diag_scan", {"mac":"ED:ED:87:D7:27:50","adapter":"hci0","cid":c1})
a1=wait(c1, 14.0)
open(os.path.join(OUT,'c1_scan_ack.json'),'w').write(json.dumps(a1 or {}))

time.sleep(0.25)
pub(f"{BASE}/cmd/actuate_probe", {"cid":c2})
a2=wait(c2, 20.0)
open(os.path.join(OUT,'c2_actuation_ack.json'),'w').write(json.dumps(a2 or {}))

ok1=bool(a1 and a1.get('ok'))
ok2=bool(a2 and a2.get('ok'))
cid1=bool(a1 and isinstance(a1.get('raw'),dict) and a1['raw'].get('cid')==c1)
cid2=bool(a2 and isinstance(a2.get('raw'),dict) and a2['raw'].get('cid')==c2)

G2='ACCEPT' if (ok1 and ok2 and cid1 and cid2) else 'REWORK'
open(os.path.join(OUT,'G2.status'),'w').write(G2+'\n')
open(os.path.join(OUT,'g2_summary.json'),'w').write(json.dumps({
  'ok1':ok1,'ok2':ok2,'cid1':cid1,'cid2':cid2
}))

cl.loop_stop()
PY

OUT_DIR_ABS="$(cd "$OUT_DIR" && pwd)"
CID="g2-$TS-$$" MQTT_HOST="$MQTT_HOST" MQTT_PORT="$MQTT_PORT" MQTT_USER="$MQTT_USER" MQTT_PASSWORD="$MQTT_PASSWORD" MQTT_BASE="$MQTT_BASE" OUT_DIR="$OUT_DIR_ABS" python3 "$PY_G" || true

# Entity persistence test (uses HA_URL default inside script; relies on HA_TOKEN env)
set -a; export HA_TOKEN; set +a
python3 reports/checkpoints/INT-HA-CONTROL/entity_persistence_test.py || true

# Receipt (<=10 lines)
G1=$(cat "$OUT_DIR/G1.status" 2>/dev/null || echo REWORK)
G2=$(cat "$OUT_DIR/G2.status" 2>/dev/null || echo REWORK)
echo "[Gate]: G1 $G1, G2 $G2"
echo "- Add-on restart http_code: $HTTP_CODE"
if [[ -s "$OUT_DIR/g2_summary.json" ]]; then
  H=$(jq -r '"diag_scan="+(.ok1|tostring)+" cid1="+(.cid1|tostring)+" actuate_probe="+(.ok2|tostring)+" cid2="+(.cid2|tostring)' "$OUT_DIR/g2_summary.json" 2>/dev/null || true)
  echo "- Highlights: ${H:-unavailable}"
fi
if [[ -s "$OUT_DIR/telemetry.json" ]]; then
  echo "- Telemetry.connected: $(jq -r '.connected // "missing"' "$OUT_DIR/telemetry.json" 2>/dev/null || echo missing)"
fi
echo "- Evidence local: $OUT_DIR"
echo "- Next: rerun if REWORK; inspect add-on logs if needed"

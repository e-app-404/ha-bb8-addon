#!/usr/bin/env bash
# DEV-ONLY: This helper uses docker exec inside the HA host to run code in the add-on container.
# Per ADR-0031 Supervisor-only acceptance flow and testing-deployment guardrails,
# this script is NOT valid for acceptance. Use ops/evidence/run_b5_supervisor_only.sh instead.
set -Eeuo pipefail

# Governance guard: if explicitly running in supervisor-only acceptance context, bail out.
if [[ "${SUPERVISOR_ONLY:-0}" == "1" || "${ACCEPTANCE:-0}" == "1" ]]; then
    echo "ERROR: supervisor-only acceptance forbids docker exec."
    echo "Use: ops/evidence/run_b5_supervisor_only.sh (MQTT-only + HA API restarts)"
    exit 2
fi

HOST="${1:-homeassistant}"
TS="$(date -u +%Y%m%dT%H%M%SZ)"
HOST_BASE="/config/ha-bb8"
HOST_EVID="${HOST_BASE}/checkpoints/BB8-FUNC/${TS}"
LOCAL_DIR="reports/checkpoints/BB8-FUNC/ssh_b5_${TS}"

# Execute remote runner with forwarded MQTT creds and consistent TS (DEV ONLY)
ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new "${HOST}" "MQTT_USER=\"${MQTT_USER:-}\" MQTT_PASSWORD=\"${MQTT_PASSWORD:-}\" TS='${TS}' bash -s" <<'REMOTE'
set -Eeuo pipefail
CID="$(docker ps --format '{{.ID}} {{.Names}} {{.Image}}' | awk 'tolower($0) ~ /bb8/ {print $1; exit}')"
if [ -z "$CID" ]; then
  echo "ERROR: BB-8 add-on container not found" >&2
  docker ps --format '{{.ID}} {{.Names}} {{.Image}}' >&2
  exit 1
fi
IN_DIR="/data/reports/checkpoints/BB8-FUNC/${TS}"
HOST_DIR="/config/ha-bb8/checkpoints/BB8-FUNC/${TS}"
docker exec "$CID" sh -lc "mkdir -p '$IN_DIR'"

RUNNER="/tmp/b5_e2e_run.py"
cat > "$RUNNER" <<'PY'
import os, json, time
from datetime import datetime, timezone
import paho.mqtt.client as mqtt

BROKER='core-mosquitto'
BASE='bb8'
CIDS=['b5-1','b5-2','b5-3','b5-4','b5-5']
DIR=os.environ.get('EVID_DIR','/data/reports/checkpoints/BB8-FUNC/TS_UNSET')
LOG=f"{DIR}/b5_e2e_demo.log"
SUM=f"{DIR}/b5_summary.md"
TELEMETRY_JSON=f"{DIR}/telemetry.json"
RES_JSON=f"{DIR}/results.json"
G1_STATUS=f"{DIR}/G1.status"
G2_STATUS=f"{DIR}/G2.status"

acks={}
tele={'connected':None,'estop':None,'last_cmd_ts':None,'battery':None}
status='unknown'
timeline=[]

def iso(): return datetime.now(timezone.utc).isoformat()

def on_message(cl,ud,msg):
    global status
    s=msg.payload.decode('utf-8','ignore')
    timeline.append(f"{iso()} {msg.topic} {s}")
    if msg.topic.startswith(f"{BASE}/ack/"):
        try:
            d=json.loads(s); cid=d.get('cid'); ok=bool(d.get('ok'))
            if cid: acks[cid]={'ok':ok,'ts':time.time(),'raw':d}
        except: pass
    if msg.topic == f"{BASE}/status/telemetry":
        try:
            d=json.loads(s)
            for k in tele: tele[k]=d.get(k,tele[k])
        except: pass
    if msg.topic == f"{BASE}/status":
        status = s.strip().lower()

cl=mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
u=os.getenv('MQTT_USER'); p=os.getenv('MQTT_PASSWORD')
if u and p: cl.username_pw_set(u, p)

rc=cl.connect(BROKER)
timeline.append(f"{iso()} mqtt/connect rc={rc}")
cl.on_message=on_message
cl.subscribe([(f"{BASE}/ack/#",0),(f"{BASE}/status/#",0),(f"{BASE}/event/#",0)])
cl.loop_start()

def pub(t,o): cl.publish(t, json.dumps(o), qos=0, retain=False)

# Pre-wait for telemetry presence up to 30s (G1 criterion: presence of 'connected' field)
t0=time.time()
while time.time()-t0<30.0 and tele['connected'] is None:
    time.sleep(0.05)
try:
    with open(TELEMETRY_JSON,'w',encoding='utf-8') as f:
        json.dump(tele, f, ensure_ascii=False)
except Exception:
    pass

def wait_ack(cid, to=15.0):
    t0=time.time()
    while time.time()-t0<to:
        if cid in acks: return True, int((time.time()-t0)*1000), acks[cid]
        time.sleep(0.02)
    return False, int(to*1000), None

steps=[
    (f"{BASE}/cmd/power",      {"action":"wake","cid":CIDS[0]}),
    (f"{BASE}/cmd/led_preset", {"name":"sunset","cid":CIDS[1]}),
    (f"{BASE}/cmd/drive",      {"speed":120,"heading":90,"ms":1500,"cid":CIDS[2]}),
    (f"{BASE}/cmd/stop",       {"cid":CIDS[3]}),
    (f"{BASE}/cmd/power",      {"action":"sleep","cid":CIDS[4]}),
]
results=[]
for i,(topic,payload) in enumerate(steps):
    if i==0: time.sleep(0.5)
    elif i==1: time.sleep(1.0)
    else: time.sleep(0.4)
    pub(topic,payload)
    ok,ms,ack=wait_ack(payload['cid'], 15.0)
    # CID correlation: ensure ack contains the expected cid and ok==true
    cid_match = bool(ack and isinstance(ack.get('raw'), dict) and ack['raw'].get('cid') == payload['cid'])
    ack_ok = bool(ok and ack and ack.get('ok'))
    results.append({"cid":payload['cid'],"topic":topic,"ok": bool(ack_ok and cid_match), "ack_latency_ms": ms, "cid_match": cid_match})
    if not (ok and ack and ack.get('ok')): break

cl.loop_stop()
os.makedirs(os.path.dirname(LOG), exist_ok=True)
open(LOG,'w',encoding='utf-8').write("\n".join(timeline)+"\n")
ok_results=[r for r in results if r['ok']]
mean=int(sum(r['ack_latency_ms'] for r in ok_results)/max(1,len(ok_results)))
verdict='PASS' if all(r['ok'] for r in results) else 'FAIL'
with open(SUM,'w',encoding='utf-8') as f:
    f.write(f"[B5 E2E]: {verdict}\n")
    f.write(f"ACKs: {sum(1 for r in results if r['ok'])}/{len(results)} (mean {mean} ms)\n")
    f.write(f"Telemetry: connected={tele['connected']} estop={tele['estop']} last_cmd_ts={tele['last_cmd_ts']} battery={tele['battery']}\n")
    f.write("Evidence: b5_e2e_demo.log, b5_summary.md\n")

# Persist machine-readable results and gate statuses
try:
    with open(RES_JSON,'w',encoding='utf-8') as rf:
        json.dump({"results":results,"telemetry":tele}, rf, ensure_ascii=False)
except Exception:
    pass

# G1: ACCEPT if telemetry contains 'connected' key (presence within pre-wait)
try:
    open(G1_STATUS,'w').write('ACCEPT\n' if tele.get('connected', None) is not None else 'REWORK\n')
except Exception:
    pass

# G2: ACCEPT if every step produced ok True with CID correlation
try:
    g2_ok = bool(results) and all(r.get('ok', False) and r.get('cid_match', False) for r in results)
    open(G2_STATUS,'w').write('ACCEPT\n' if g2_ok else 'REWORK\n')
except Exception:
    pass

# Echo probe
try:
    state={'ok': False}; t0=time.time()
    def on_echo(c,u2,m):
        if m.topic==f"{BASE}/echo/state" and b'"source":"device"' in m.payload:
            state['ok']=True; c.loop_stop()
    e=mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    if u and p: e.username_pw_set(u,p)
    if e.connect(BROKER)==0:
        e.on_message=on_echo
        e.subscribe([(f"{BASE}/echo/state",0)]); e.loop_start()
        e.publish(f"{BASE}/echo/cmd", json.dumps({"cid":"echo-b5","ping":True}))
        t1=time.time()
        while time.time()-t1<5 and not state['ok']: time.sleep(0.02)
    rt=int((time.time()-t0)*1000)
    open(SUM,'a',encoding='utf-8').write(f"Echo health: {'green' if state['ok'] else 'fail'} (round-trip {rt} ms)\n")
except Exception as ex:
    open(SUM,'a',encoding='utf-8').write(f"Echo health: error ({ex})\n")
PY

docker cp "$RUNNER" "$CID:/tmp/b5_e2e_run.py"
# Pick available Python inside the add-on container
PYBIN="$(docker exec "$CID" sh -lc 'command -v python3 || command -v python || true')"
if [ -z "$PYBIN" ]; then
    echo "ERROR: No python interpreter found in container $CID" >&2
    exit 127
fi
docker exec -e EVID_DIR="$IN_DIR" -e MQTT_USER -e MQTT_PASSWORD "$CID" sh -lc "$PYBIN /tmp/b5_e2e_run.py"

mkdir -p "$HOST_DIR"
docker cp "$CID:${IN_DIR}/." "$HOST_DIR/"
ls -la "$HOST_DIR" || true
REMOTE

# Pull evidence locally
mkdir -p "${LOCAL_DIR}"
rsync -avz -e ssh "${HOST}:${HOST_EVID}/" "${LOCAL_DIR}/" >/dev/null 2>&1 || true

# Print concise receipt (<=10 lines)
G1="$(cat "${LOCAL_DIR}/G1.status" 2>/dev/null || echo REWORK)"
G2="$(cat "${LOCAL_DIR}/G2.status" 2>/dev/null || echo REWORK)"
echo "[Gate]: G1 ${G1}, G2 ${G2}"
if [ -f "${LOCAL_DIR}/results.json" ]; then
    OKS=$(jq -r '[.results[] | select(.ok==true)] | length' "${LOCAL_DIR}/results.json" 2>/dev/null || echo "?")
    TOT=$(jq -r '.results | length' "${LOCAL_DIR}/results.json" 2>/dev/null || echo "?")
    echo "- ACKs: ${OKS}/${TOT}"
fi
if [ -f "${LOCAL_DIR}/telemetry.json" ]; then
    CONN=$(jq -r '.connected // empty' "${LOCAL_DIR}/telemetry.json" 2>/dev/null || echo "")
    echo "- Telemetry.connected: ${CONN:-present}"
else
    echo "- Telemetry.connected: missing"
fi
echo "- Evidence local: ${LOCAL_DIR}"
echo "- Next: if G2=REWORK → check add-on logs and command handlers"
echo "EVIDENCE_LOCAL_DIR=${LOCAL_DIR}"

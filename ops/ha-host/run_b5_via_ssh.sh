#!/usr/bin/env bash
set -Eeuo pipefail

HOST="${1:-homeassistant}"            # or hass-root
TS="$(date -u +%Y%m%dT%H%M%SZ)"
HOST_BASE="/config/ha-bb8"
HOST_EVID="${HOST_BASE}/checkpoints/BB8-FUNC/${TS}"
LOCAL_DIR="reports/checkpoints/BB8-FUNC/ssh_b5_${TS}"

# Run remote actions with creds forwarded into the ssh session's env
ssh -o BatchMode=yes "${HOST}" "MQTT_USER=\"${MQTT_USER:-}\" MQTT_PASSWORD=\"${MQTT_PASSWORD:-}\" bash -s" <<'REMOTE'
set -Eeuo pipefail
CID="$(docker ps --format '{{.ID}} {{.Names}} {{.Image}}' | awk 'tolower($0) ~ /bb8/ {print $1; exit}')"
if [ -z "$CID" ]; then
  echo "ERROR: BB-8 add-on container not found" >&2
  docker ps --format '{{.ID}} {{.Names}} {{.Image}}' >&2
  exit 1
fi
TS="$(date -u +%Y%m%dT%H%M%SZ)"
IN_DIR="/data/reports/checkpoints/BB8-FUNC/${TS}"
HOST_DIR="/config/ha-bb8/checkpoints/BB8-FUNC/${TS}"
docker exec "$CID" sh -lc "mkdir -p '$IN_DIR'"

# Write Python runner to host /tmp and copy into container
RUNNER_HOST_PY="/tmp/b5_runner.py"
cat >"${RUNNER_HOST_PY}" <<'PY'
import os, json, time
from datetime import datetime, timezone
import paho.mqtt.client as mqtt

BROKER='core-mosquitto'
BASE='bb8'
CIDS=['b5-1','b5-2','b5-3','b5-4','b5-5']
DIR=os.environ.get('EVID_DIR','/data/reports/checkpoints/BB8-FUNC/TS_UNSET')
LOG=f"{DIR}/b5_e2e_demo.log"
SUM=f"{DIR}/b5_summary.md"

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
if rc != 0:
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    open(LOG,'w',encoding='utf-8').write("\n".join(timeline)+"\n")
    with open(SUM,'w',encoding='utf-8') as f:
        f.write("[B5 E2E]: REWORK\n")
        f.write(f"Connect rc={rc} (likely auth)\nEvidence: b5_e2e_demo.log, b5_summary.md\n")
    raise SystemExit(2)

cl.on_message=on_message
cl.subscribe([(f"{BASE}/ack/#",0),(f"{BASE}/status/#",0),(f"{BASE}/event/#",0)])
cl.loop_start()

def pub(t,o): cl.publish(t, json.dumps(o), qos=0, retain=False)
def wait_ack(cid, to=15.0):
    t0=time.time()
    while time.time()-t0<to:
        if cid in acks: return True, int((time.time()-t0)*1000), acks[cid]
        time.sleep(0.02)
    return False, int(to*1000), None
def wait_online(to=30.0):
    t0=time.time()
    while time.time()-t0<to:
        if status=='online' or tele['connected'] is True:
            return True, int((time.time()-t0)*1000)
        time.sleep(0.05)
    return False, int(to*1000)

ok_online, ms_online = wait_online(30.0)
if not ok_online:
    pub(f"{BASE}/cmd/power", {"action":"wake","cid":"warmup"})
    time.sleep(0.5)
    ok_online, ms_online = wait_online(30.0)

steps=[
    (f"{BASE}/cmd/power",      {"action":"wake","cid":CIDS[0]}),
    (f"{BASE}/cmd/led_preset", {"name":"sunset","cid":CIDS[1]}),
    (f"{BASE}/cmd/drive",      {"speed":120,"heading":90,"ms":1500,"cid":CIDS[2]}),
    (f"{BASE}/cmd/stop",       {"cid":CIDS[3]}),
    (f"{BASE}/cmd/power",      {"action":"sleep","cid":CIDS[4]}),
]

results=[]
if ok_online:
    for i,(topic,payload) in enumerate(steps):
        if i==0: pass
        elif i==1: time.sleep(0.5)
        else: time.sleep(0.3)
        pub(topic,payload)
        ok,ms,ack=wait_ack(payload['cid'], 15.0)
        results.append({"cid":payload['cid'],"topic":topic,"ok": bool(ok and ack and ack["ok"]), "ack_latency_ms": ms})
        if not (ok and ack and ack["ok"]): break
else:
    results=[{"cid":"warmup","topic":f"{BASE}/cmd/power","ok":False,"ack_latency_ms":ms_online}]

cl.loop_stop()
os.makedirs(os.path.dirname(LOG), exist_ok=True)
open(LOG,'w',encoding='utf-8').write("\n".join(timeline)+"\n")
ok_results=[r for r in results if r['ok']]
mean=int(sum(r['ack_latency_ms'] for r in ok_results)/max(1,len(ok_results)))
verdict='PASS' if all(r['ok'] for r in results) and ok_online else 'REWORK' if not ok_online else 'FAIL'

with open(SUM,'w',encoding='utf-8') as f:
    f.write(f"[B5 E2E]: {verdict}\n")
    f.write(f"Online gate: {'ok' if ok_online else 'timeout'} ({ms_online} ms)\n")
    f.write(f"ACKs: {sum(1 for r in results if r['ok'])}/{len(results)} (mean {mean} ms)\n")
    f.write(f"Telemetry: connected={tele['connected']} estop={tele['estop']} last_cmd_ts={tele['last_cmd_ts']} battery={tele['battery']}\n")
    f.write("Evidence: b5_e2e_demo.log, b5_summary.md\n")
PY

docker cp "${RUNNER_HOST_PY}" "${CID}:/tmp/b5_runner.py"
docker exec -e EVID_DIR="${IN_DIR}" -e MQTT_USER -e MQTT_PASSWORD "${CID}" python3 /tmp/b5_runner.py || true

# Echo probe: write small script and run
ECHO_HOST_PY="/tmp/echo_probe.py"
cat >"${ECHO_HOST_PY}" <<'PY'
import os, json, time
from datetime import datetime, timezone
import paho.mqtt.client as mqtt
BROKER='core-mosquitto'; BASE='bb8'; CID='echo-b5'
DIR=os.environ.get('EVID_DIR','/data/reports/checkpoints/BB8-FUNC/TS_UNSET')
SUM=f"{DIR}/b5_summary.md"
u=os.getenv('MQTT_USER'); p=os.getenv('MQTT_PASSWORD')
cl=mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
if u and p: cl.username_pw_set(u,p)
ok=False; t0=time.time()
def on_message(c,u2,m):
    global ok
    if m.topic==f"{BASE}/echo/state" and b'"source":"device"' in m.payload:
        ok=True; c.loop_stop()
cl.on_message=on_message; rc=cl.connect(BROKER)
if rc==0:
    cl.subscribe([(f"{BASE}/echo/state",0)]); cl.loop_start()
    cl.publish(f"{BASE}/echo/cmd", json.dumps({"cid":CID,"ping":True}))
    t1=time.time()
    while time.time()-t1<5 and not ok: time.sleep(0.02)
rt_ms=int((time.time()-t0)*1000)
open(SUM,'a',encoding='utf-8').write(f"Echo health: {'green' if ok else 'fail'} (round-trip {rt_ms} ms)\n")
PY

docker cp "${ECHO_HOST_PY}" "${CID}:/tmp/echo_probe.py"
docker exec -e EVID_DIR="${IN_DIR}" -e MQTT_USER -e MQTT_PASSWORD "${CID}" python3 /tmp/echo_probe.py || true

# Stage evidence to host path and list
mkdir -p "$HOST_DIR"
docker cp "$CID:${IN_DIR}/." "$HOST_DIR/"
ls -la "$HOST_DIR" || true
REMOTE

# Pull evidence locally and print path
mkdir -p "${LOCAL_DIR}"
rsync -avz -e ssh "${HOST}:${HOST_EVID}/" "${LOCAL_DIR}/" >/dev/null 2>&1 || true
echo "EVIDENCE_LOCAL_DIR=${LOCAL_DIR}"
#!/usr/bin/env bash
set -Eeuo pipefail

HOST="${1:-homeassistant}"           # e.g., homeassistant or hass-root
TS="$(date -u +%Y%m%dT%H%M%SZ)"
HOST_BASE="/config/ha-bb8"           # host-confined path
HOST_EVIDENCE_DIR="${HOST_BASE}/checkpoints/BB8-FUNC/${TS}"
LOCAL_CAPTURE_DIR="reports/checkpoints/BB8-FUNC/ssh_b5_${TS}"

# Create host evidence dir
ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new "${HOST}" "mkdir -p '${HOST_EVIDENCE_DIR}'"

# Execute remote sequence: find container, run runner writing to /data, then copy to host path
ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new "${HOST}" bash -s <<'REMOTE'
set -Eeuo pipefail
CID="$(docker ps --format '{{.ID}} {{.Names}} {{.Image}}' | awk 'tolower($0) ~ /bb8/ {print $1; exit}')"
if [ -z "${CID}" ]; then
  echo "ERROR: BB-8 add-on container not found" >&2
  docker ps --format '{{.ID}} {{.Names}} {{.Image}}' >&2
  exit 1
fi
TS="$(date -u +%Y%m%dT%H%M%SZ)"
HOST_BASE="/config/ha-bb8"
HOST_EVIDENCE_DIR="${HOST_BASE}/checkpoints/BB8-FUNC/${TS}"
IN_CONTAINER_DIR="/data/reports/checkpoints/BB8-FUNC/${TS}"

docker exec "${CID}" sh -lc "mkdir -p '${IN_CONTAINER_DIR}'"

# Inline Python runner; pass EVID_DIR and creds/env through
HOST_TMP_DIR="/tmp"
HOST_RUNNER_PY="${HOST_TMP_DIR}/b5_runner.py"
cat >"${HOST_RUNNER_PY}" <<'PY'
import os, json, time
from datetime import datetime, timezone
import paho.mqtt.client as mqtt

BROKER='core-mosquitto'
BASE='bb8'
CIDS=['b5-1','b5-2','b5-3','b5-4','b5-5']
DIR=os.environ.get('EVID_DIR','/data/reports/checkpoints/BB8-FUNC/TS_UNSET')
LOG_PATH=f"{DIR}/b5_e2e_demo.log"
SUM_PATH=f"{DIR}/b5_summary.md"

acks={}
tele={'connected':None,'estop':None,'last_cmd_ts':None,'battery':None}
timeline=[]
def iso(): return datetime.now(timezone.utc).isoformat()

def on_message(cl,ud,msg):
    s=msg.payload.decode('utf-8','ignore')
    timeline.append(f"{iso()} {msg.topic} {s}")
    if msg.topic.startswith(f"{BASE}/ack/"):
        try:
            d=json.loads(s); cid=d.get('cid'); ok=bool(d.get('ok'))
            if cid: acks[cid]={'ok':ok,'ts':time.time(),'raw':d}
        except: pass
    elif msg.topic==f"{BASE}/status/telemetry":
        try:
            d=json.loads(s)
            for k in tele: tele[k]=d.get(k,tele[k])
        except: pass

cl=mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
u=os.getenv('MQTT_USER'); p=os.getenv('MQTT_PASSWORD')
if u and p: cl.username_pw_set(u, p)

rc = cl.connect(BROKER)
timeline.append(f"{iso()} mqtt/connect rc={rc}")
os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
open(LOG_PATH,'w',encoding='utf-8').write("\n".join(timeline)+"\n")
if rc != 0:
    with open(SUM_PATH,'w',encoding='utf-8') as f:
        f.write("[B5 E2E]: REWORK\n")
        f.write(f"Connect rc={rc} (likely auth if DNS/ping OK)\n")
        f.write("Evidence: b5_e2e_demo.log, b5_summary.md\n")
    raise SystemExit(2)

cl.on_message=on_message
cl.subscribe([(f"{BASE}/ack/#",0),(f"{BASE}/status/#",0),(f"{BASE}/event/#",0)])
cl.loop_start()

def pub(t,o): cl.publish(t, json.dumps(o), qos=0, retain=False)
def wait_ack(cid, to=10.0):
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
for topic,payload in steps:
    pub(topic,payload)
    ok,ms,ack=wait_ack(payload['cid'])
    results.append({"cid":payload['cid'],"topic":topic,"ok": bool(ok and ack and ack.get('ok')), "ack_latency_ms": ms})
    if not (ok and ack and ack.get('ok')): break

cl.loop_stop()
open(LOG_PATH,'w',encoding='utf-8').write("\n".join(timeline)+"\n")
ok_results=[r for r in results if r['ok']]
mean=int(sum(r['ack_latency_ms'] for r in ok_results)/max(1,len(ok_results)))
verdict='PASS' if all(r['ok'] for r in results) else 'FAIL'
with open(SUM_PATH,'w',encoding='utf-8') as f:
    f.write(f"[B5 E2E]: {verdict}\n")
    f.write(f"ACKs: {sum(1 for r in results if r['ok'])}/{len(results)} (mean {mean} ms)\n")
    f.write(f"Telemetry: connected={tele['connected']} estop={tele['estop']} last_cmd_ts={tele['last_cmd_ts']} battery={tele['battery']}\n")
    f.write("Evidence: b5_e2e_demo.log, b5_summary.md\n")
PY
docker cp "${HOST_RUNNER_PY}" "${CID}:/tmp/b5_runner.py"
docker exec -e EVID_DIR="${IN_CONTAINER_DIR}" -e MQTT_USER -e MQTT_PASSWORD "${CID}" python3 /tmp/b5_runner.py || true

# Echo health append (pass creds)
HOST_ECHO_PY="${HOST_TMP_DIR}/echo_probe.py"
cat >"${HOST_ECHO_PY}" <<'PY'
import os, json, time
from datetime import datetime, timezone
import paho.mqtt.client as mqtt
BROKER='core-mosquitto'; BASE='bb8'; CID='echo-b5'
DIR=os.environ.get('EVID_DIR','/data/reports/checkpoints/BB8-FUNC/TS_UNSET')
SUM=f"{DIR}/b5_summary.md"
u=os.getenv('MQTT_USER'); p=os.getenv('MQTT_PASSWORD')
cl=mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
if u and p: cl.username_pw_set(u,p)
ok=False; t0=time.time()
def on_message(c,u2,m):
    global ok
    if m.topic==f"{BASE}/echo/state" and b'"source":"device"' in m.payload:
        ok=True; c.loop_stop()
cl.on_message=on_message; rc=cl.connect(BROKER)
if rc==0:
    cl.subscribe([(f"{BASE}/echo/state",0)]); cl.loop_start()
    cl.publish(f"{BASE}/echo/cmd", json.dumps({"cid":CID,"ping":True}))
    t1=time.time()
    while time.time()-t1<5 and not ok: time.sleep(0.02)
rt_ms=int((time.time()-t0)*1000)
open(SUM,'a',encoding='utf-8').write(f"Echo health: {'green' if ok else 'fail'} (round-trip {rt_ms} ms)\n")
PY
docker cp "${HOST_ECHO_PY}" "${CID}:/tmp/echo_probe.py"
docker exec -e EVID_DIR="${IN_CONTAINER_DIR}" -e MQTT_USER -e MQTT_PASSWORD "${CID}" python3 /tmp/echo_probe.py || true

# Copy evidence from container to host path
mkdir -p "${HOST_EVIDENCE_DIR}"
docker cp "${CID}:${IN_CONTAINER_DIR}/." "${HOST_EVIDENCE_DIR}/"
REMOTE

# Pull evidence locally
mkdir -p "${LOCAL_CAPTURE_DIR}"
rsync -avz -e ssh "${HOST}:${HOST_EVIDENCE_DIR}/" "${LOCAL_CAPTURE_DIR}/" >/dev/null 2>&1 || true
echo "EVIDENCE_LOCAL_DIR=${LOCAL_CAPTURE_DIR}"

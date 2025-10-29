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

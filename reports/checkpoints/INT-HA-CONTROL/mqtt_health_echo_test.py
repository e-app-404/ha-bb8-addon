#!/usr/bin/env python3
import argparse, time, json, sys
from datetime import datetime
try:
    import paho.mqtt.client as mqtt
except Exception as e:
    print("PAHO_IMPORT_FAIL:", e)
    sys.exit(2)

parser = argparse.ArgumentParser()
parser.add_argument('--host', required=True)
parser.add_argument('--port', type=int, default=1883)
parser.add_argument('--user')
parser.add_argument('--password')
parser.add_argument('--base', required=True)
parser.add_argument('--sla-ms', type=int, default=1000)
parser.add_argument('--pings', type=int, default=5)
parser.add_argument('--out', required=True)
args = parser.parse_args()

TOPIC_CMD=f"{args.base}/echo/cmd"
TOPIC_ACK=f"{args.base}/echo/ack"
results=[]

client=mqtt.Client()
if args.user:
    client.username_pw_set(args.user, args.password)

ack_payload=None
start_ts=None

def on_connect(c,u,flags,rc):
    c.subscribe(TOPIC_ACK)

def on_message(c,u,msg):
    global ack_payload
    ack_payload=(msg.topic, msg.payload.decode('utf-8','ignore'), time.time())

client.on_connect=on_connect
client.on_message=on_message
client.connect(args.host, args.port, 30)
client.loop_start()

for i in range(args.pings):
    start=time.time()
    client.publish(TOPIC_CMD, f"ping:{i}:{int(start*1000)}")
    deadline=start + (args.sla_ms/1000.0)
    ack_payload=None
    while time.time() < deadline and ack_payload is None:
        time.sleep(0.01)
    if ack_payload:
        lat_ms=int((ack_payload[2]-start)*1000)
        results.append({"i":i, "ok":True, "latency_ms":lat_ms})
    else:
        results.append({"i":i, "ok":False, "latency_ms":None})
    time.sleep(0.1)

client.loop_stop()

ok=sum(1 for r in results if r['ok'])
with open(args.out,'w') as f:
    f.write("# mqtt_roundtrip.log\n")
    f.write(f"ts={datetime.utcnow().isoformat()}Z\n")
    for r in results:
        f.write(json.dumps(r)+"\n")

summary={"echo_ok": ok==args.pings and all(r['latency_ms'] is not None and r['latency_ms']<=args.sla_ms for r in results),
         "ok_count": ok,
         "max_latency_ms": max([r['latency_ms'] or 99999 for r in results]),
         "results": results}
print(json.dumps(summary))

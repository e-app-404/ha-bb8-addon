#!/bin/bash
python3 - <<'PY'
import json, os
import paho.mqtt.client as mqtt
from paho.mqtt.client import CallbackAPIVersion

HOST=os.getenv("MQTT_HOST","192.168.0.129")
USER=os.getenv("MQTT_USER","mqtt_bb8")
PWD =os.getenv("MQTT_PASSWORD","mqtt_bb8")
BASE=os.getenv("MQTT_BASE","bb8")

c = mqtt.Client(protocol=mqtt.MQTTv5, callback_api_version=CallbackAPIVersion.VERSION2)
c.username_pw_set(USER, PWD)

def pub(topic, payload, qos=1, retain=False):
    if isinstance(payload,(dict,list)):
        payload=json.dumps(payload, ensure_ascii=False)
    c.publish(topic, payload, qos=qos, retain=retain)

def on_msg(_c,_u,m):
    t=m.topic
    try: s=m.payload.decode("utf-8","ignore").strip()
    except: s=""
    if t==f"{BASE}/power/set":
        v=s.upper()
        if v in ("ON","OFF"):
            pub(f"{BASE}/power/state", {"value":v, "source":"facade"}, qos=1, retain=True)
    elif t==f"{BASE}/stop/press":
        pub(f"{BASE}/stop/state","pressed", qos=1, retain=False)
        pub(f"{BASE}/stop/state","idle", qos=1, retain=False)
    elif t==f"{BASE}/led/set":
        try:
            d=json.loads(s) if s else {}
            if "hex" in d:
                hx=d["hex"].lstrip("#")
                d={"r":int(hx[0:2],16),"g":int(hx[2:4],16),"b":int(hx[4:6],16)}
            elif {"r","g","b"}.issubset(d): d={"r":int(d["r"]), "g":int(d["g"]), "b":int(d["b"])}
            else: return
            pub(f"{BASE}/led/state", d, qos=1, retain=True)
        except: pass
    elif t==f"{BASE}/sleep/press":
        pub(f"{BASE}/sleep/state","pressed", qos=1, retain=False)
        pub(f"{BASE}/sleep/state","idle", qos=1, retain=False)
    elif t==f"{BASE}/heading/set":
        pub(f"{BASE}/heading/state",s, qos=1, retain=True)
    elif t==f"{BASE}/speed/set":
        pub(f"{BASE}/speed/state",s, qos=1, retain=True)
    elif t==f"{BASE}/drive/press":
        pub(f"{BASE}/drive/state","pressed", qos=1, retain=False)
        pub(f"{BASE}/drive/state","idle", qos=1, retain=False)

c.on_message = on_msg
c.connect(HOST, 1883, 60)
c.subscribe([
    (f"{BASE}/power/set",1),
    (f"{BASE}/stop/press",1),
    (f"{BASE}/led/set",1),
    (f"{BASE}/sleep/press",1),
    (f"{BASE}/heading/set",1),
    (f"{BASE}/speed/set",1),
    (f"{BASE}/drive/press",1),
])
c.publish(f"{BASE}/presence/state", "ON", qos=1, retain=True)
c.publish(f"{BASE}/rssi/state", "-70", qos=1, retain=True)
c.loop_forever()
PY

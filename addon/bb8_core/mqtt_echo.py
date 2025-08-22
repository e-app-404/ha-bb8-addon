import json


def echo_scalar(mqtt, base, topic, value, *, source="device"):
    payload = json.dumps({"value": value, "source": source})
    mqtt.publish(f"{base}/{topic}/state", payload, qos=0, retain=False)


def echo_led(mqtt, base, r, g, b):
    payload = json.dumps({"r": r, "g": g, "b": b})
    mqtt.publish(f"{base}/led/state", payload, qos=0, retain=False)

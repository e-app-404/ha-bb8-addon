import json
import logging


def echo_scalar(mqtt, base, topic, value, *, source="device"):
    try:
        payload = json.dumps({"value": value, "source": source})
        mqtt.publish(f"{base}/{topic}/state", payload, qos=0, retain=False)
        logging.debug(f"echo_scalar published: {base}/{topic}/state {payload}")
    except Exception as e:
        logging.error(f"echo_scalar failed: {e}")


def echo_led(mqtt, base, r, g, b):
    try:
        payload = json.dumps({"r": r, "g": g, "b": b})
        mqtt.publish(f"{base}/led/state", payload, qos=0, retain=False)
        logging.debug(f"echo_led published: {base}/led/state {payload}")
    except Exception as e:
        logging.error(f"echo_led failed: {e}")

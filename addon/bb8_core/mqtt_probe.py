#!/usr/bin/env python
import argparse
import json
import os
import threading
import time

import paho.mqtt.client as mqtt


def env(name, default=None, required=False):
    """Retrieve an environment variable value with optional default and required checks.

    Args:
        name (str): The name of the environment variable to retrieve.
        default (Any, optional): The default value to return if the environment variable is not set. Defaults to None.
        required (bool, optional): If True, raises SystemExit if the environment variable is missing or empty. Defaults to False.

    Returns:
        str: The value of the environment variable as a string, or the default value if not set.

    Raises:
        SystemExit: If `required` is True and the environment variable is missing or empty.

    """
    v = os.environ.get(name, default)
    if required and (v is None or v == ""):
        raise SystemExit(f"[probe] missing env {name}")
    if v is None:
        v = ""
    return str(v)


def main():
    """Probes an MQTT broker for connectivity and device echo response.

    This function connects to an MQTT broker using credentials and
    configuration from environment variables. It publishes a test command
    to a device echo topic, waits for a response, and evaluates the roundtrip
    and schema validity.

    Command-line arguments:
        --timeout (int): Maximum time in seconds to wait for echo response
            (default: 8).
        --require-echo (str): Whether device echo is required to pass
            (default: "1").

    Environment variables:
        MQTT_HOST (str): Hostname or IP address of the MQTT broker (required).
        MQTT_PORT (str): Port number of the MQTT broker (default: "1883").
        MQTT_USERNAME (str): Username for MQTT authentication (optional).
        MQTT_PASSWORD (str): Password for MQTT authentication (optional).
        MQTT_BASE (str): Base topic for MQTT messages (default: "bb8").
        REQUIRE_DEVICE_ECHO (str): If set to "1", require device echo for
            success (default: "1").

    Behavior:
        - Connects to the MQTT broker and subscribes to echo topics.
        - Publishes a test command to the echo command topic.
        - Waits for an echo response within the specified timeout.
        - Checks if the response is from a device and if the schema is valid.
        - Prints probe results and exits with status code:
            2 if connection failed,
            3 if roundtrip failed and device echo is required.

    Raises:
        SystemExit: If connection or roundtrip requirements are not met.

    """
    ap = argparse.ArgumentParser()
    ap.add_argument("--timeout", type=int, default=8)
    ap.add_argument("--require-echo", default="1")
    args = ap.parse_args()

    host = env("MQTT_HOST", default="", required=True)
    port = int(env("MQTT_PORT", "1883"))
    user = env("MQTT_USERNAME")
    pwd = env("MQTT_PASSWORD")
    base = env("MQTT_BASE", "bb8")

    client = mqtt.Client(client_id=f"probe-{int(time.time())}")
    if user:
        client.username_pw_set(user, pwd or None)
    res = {"connected": False, "roundtrip": "FAIL", "schema": "UNKNOWN"}
    got_echo = threading.Event()
    payload_seen: dict | None = None

    def on_message(c, ud, msg):
        nonlocal payload_seen
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
        except Exception:
            return
        if msg.topic == f"{base}/echo/state":
            payload_seen = payload
            got_echo.set()

    def on_connect(c, ud, flags, rc, props=None):
        if rc == 0:
            res["connected"] = True
            c.subscribe([(f"{base}/#", 0)])
            cmd = {"value": 1, "ts": int(time.time())}
            c.publish(f"{base}/echo/cmd", json.dumps(cmd), qos=0, retain=False)

    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(host, port, keepalive=10)
    client.loop_start()
    got_echo.wait(timeout=args.timeout)
    client.loop_stop()
    client.disconnect()

    if got_echo.is_set() and payload_seen:
        if payload_seen.get("source") == "device":
            res["roundtrip"] = "PASS"
        else:
            res["roundtrip"] = "FAIL"
        res["schema"] = "PASS" if "source" in payload_seen else "FAIL"

    print(
        f"probe: connected={res['connected']} "
        f"roundtrip={res['roundtrip']} "
        f"schema={res['schema']}",
    )
    if not res["connected"]:
        raise SystemExit(2)
    if res["roundtrip"] != "PASS" and os.environ.get("REQUIRE_DEVICE_ECHO", "1") == "1":
        raise SystemExit(3)


if __name__ == "__main__":
    main()

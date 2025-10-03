#!/usr/bin/env python3
"""
INT-HA-CONTROL P1 MQTT Health Echo Test
Tests health echo functionality: send ping on bb8/health/ping, expect echo on bb8/health/echo
SLA requirement: ping→echo ≤1s
"""

import json
import os
import threading
import time
from datetime import datetime

import paho.mqtt.client as mqtt
from paho.mqtt.client import CallbackAPIVersion

# Configuration
MQTT_HOST = os.environ.get("MQTT_HOST", "192.168.0.129")
MQTT_PORT = int(os.environ.get("MQTT_PORT", "1883"))
MQTT_USER = os.environ.get("MQTT_USERNAME", "mqtt_bb8")
MQTT_PASS = os.environ.get("MQTT_PASSWORD", "mqtt_bb8")
MQTT_BASE = os.environ.get("MQTT_BASE", "bb8")

PING_TOPIC = f"{MQTT_BASE}/health/ping"
ECHO_TOPIC = f"{MQTT_BASE}/health/echo"
# Alternative: use existing echo infrastructure
ALT_PING_TOPIC = f"{MQTT_BASE}/echo/cmd"
ALT_ECHO_TOPIC = f"{MQTT_BASE}/echo/state"

CHECKPOINT_DIR = "/Users/evertappels/Projects/HA-BB8/reports/checkpoints/INT-HA-CONTROL"
SLA_THRESHOLD_SEC = 1.0


class HealthEchoTest:
    def __init__(self):
        self.client = mqtt.Client(
            client_id=f"health-echo-test-{int(time.time())}",
            callback_api_version=CallbackAPIVersion.VERSION2,
        )
        self.client.username_pw_set(MQTT_USER, MQTT_PASS)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

        self.echo_received = threading.Event()
        self.ping_time = None
        self.echo_time = None
        self.echo_payload = None
        self.roundtrip_ms = None

        self.results = []
        self.logs = []

    def log_event(self, event_type, message, **kwargs):
        entry = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "message": message,
            **kwargs,
        }
        self.logs.append(entry)
        print(f"[{entry['timestamp']}] {event_type.upper()}: {message}")

    def on_connect(self, client, userdata, flags, rc, properties=None):
        if rc == 0:
            self.log_event(
                "mqtt_connect",
                "Connected to MQTT broker",
                host=MQTT_HOST,
                port=MQTT_PORT,
            )
            # Subscribe to both health echo topics (new and fallback to existing echo)
            client.subscribe([(ECHO_TOPIC, 1), (ALT_ECHO_TOPIC, 1)])
            self.log_event(
                "mqtt_subscribe",
                "Subscribed to echo topics",
                topics=[ECHO_TOPIC, ALT_ECHO_TOPIC],
            )
        else:
            self.log_event("mqtt_error", f"Connection failed with code {rc}")

    def on_message(self, client, userdata, msg):
        self.echo_time = time.time()
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
        except:
            payload = {"raw": msg.payload.decode("utf-8", errors="ignore")}

        self.echo_payload = payload

        if self.ping_time:
            self.roundtrip_ms = (self.echo_time - self.ping_time) * 1000

        self.log_event(
            "mqtt_echo_received",
            "Echo response received",
            topic=msg.topic,
            roundtrip_ms=self.roundtrip_ms,
            payload=payload,
        )
        self.echo_received.set()

    def send_ping(self, ping_id=None):
        if ping_id is None:
            ping_id = int(time.time() * 1000)

        ping_payload = {
            "ping_id": ping_id,
            "timestamp": time.time(),
            "test": "health_echo",
            "value": 1,  # For compatibility with existing echo system
        }

        self.ping_time = time.time()
        self.echo_received.clear()

        # Try health/ping first, fallback to existing echo/cmd
        try:
            self.client.publish(PING_TOPIC, json.dumps(ping_payload), qos=1)
            self.log_event(
                "mqtt_ping",
                "Health ping sent",
                topic=PING_TOPIC,
                ping_id=ping_id,
                payload=ping_payload,
            )
        except Exception:
            # Fallback to existing echo system
            self.client.publish(ALT_PING_TOPIC, json.dumps(ping_payload), qos=1)
            self.log_event(
                "mqtt_ping_fallback",
                "Ping sent via echo/cmd",
                topic=ALT_PING_TOPIC,
                ping_id=ping_id,
                payload=ping_payload,
            )

        return ping_id

    def run_health_test(self, num_pings=3):
        self.log_event(
            "test_start",
            "Starting health echo test",
            num_pings=num_pings,
            sla_threshold=SLA_THRESHOLD_SEC,
        )

        self.client.connect(MQTT_HOST, MQTT_PORT, 60)
        self.client.loop_start()

        # Wait for connection
        time.sleep(2)

        for i in range(num_pings):
            ping_id = self.send_ping()

            # Wait for echo response
            if self.echo_received.wait(timeout=SLA_THRESHOLD_SEC * 2):
                result = {
                    "ping_id": ping_id,
                    "success": True,
                    "roundtrip_ms": self.roundtrip_ms,
                    "sla_pass": self.roundtrip_ms <= (SLA_THRESHOLD_SEC * 1000),
                    "echo_payload": self.echo_payload,
                }
                self.log_event("ping_result", f"Ping {i+1} result", **result)
            else:
                result = {
                    "ping_id": ping_id,
                    "success": False,
                    "roundtrip_ms": None,
                    "sla_pass": False,
                    "error": "timeout",
                }
                self.log_event("ping_timeout", f"Ping {i+1} timeout")

            self.results.append(result)

            if i < num_pings - 1:
                time.sleep(2)  # Brief pause between pings

        self.client.loop_stop()
        self.client.disconnect()

        # Generate summary
        successful_pings = [r for r in self.results if r["success"]]
        sla_passes = [r for r in self.results if r["sla_pass"]]

        avg_roundtrip = None
        if successful_pings:
            avg_roundtrip = sum(r["roundtrip_ms"] for r in successful_pings) / len(
                successful_pings
            )

        summary = {
            "test_metadata": {
                "timestamp": datetime.now().isoformat(),
                "mqtt_host": MQTT_HOST,
                "mqtt_base": MQTT_BASE,
                "num_pings": num_pings,
                "sla_threshold_ms": SLA_THRESHOLD_SEC * 1000,
            },
            "results": {
                "total_pings": len(self.results),
                "successful_pings": len(successful_pings),
                "sla_passes": len(sla_passes),
                "avg_roundtrip_ms": avg_roundtrip,
                "pass_rate": len(sla_passes) / num_pings if num_pings > 0 else 0,
                "overall_pass": len(sla_passes) == num_pings,
            },
            "individual_results": self.results,
        }

        return summary


def main():
    test = HealthEchoTest()
    summary = test.run_health_test(num_pings=5)

    # Use canonical reports/ directory
    from pathlib import Path

    repo_root = Path(__file__).parent.parent.parent.parent
    reports_dir = repo_root / "reports"
    reports_dir.mkdir(exist_ok=True)

    # Write roundtrip log to canonical location
    with open(reports_dir / "mqtt_roundtrip.log", "w") as f:
        for entry in test.logs:
            f.write(
                f"{entry['timestamp']} {entry['event_type'].upper()}: {entry['message']}\n"
            )
            if entry.get("roundtrip_ms"):
                f.write(f"    Roundtrip: {entry['roundtrip_ms']:.2f}ms\n")

    # Write health echo summary to mandatory artifact location
    with open(reports_dir / "mqtt_health_echo.log", "w") as f:
        f.write(json.dumps(summary, indent=2))

    print("\n=== Health Echo Test Summary ===")
    print(f"Total pings: {summary['results']['total_pings']}")
    print(f"Successful: {summary['results']['successful_pings']}")
    print(f"SLA passes: {summary['results']['sla_passes']}")
    print(f"Pass rate: {summary['results']['pass_rate']:.1%}")
    print(f"Overall PASS: {summary['results']['overall_pass']}")

    if summary["results"]["avg_roundtrip_ms"]:
        print(f"Avg roundtrip: {summary['results']['avg_roundtrip_ms']:.2f}ms")

    return 0 if summary["results"]["overall_pass"] else 1


if __name__ == "__main__":
    exit(main())

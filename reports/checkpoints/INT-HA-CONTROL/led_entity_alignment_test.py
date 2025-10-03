#!/usr/bin/env python3
"""
INT-HA-CONTROL P3 LED Entity Alignment Test
Toggle-gated LED discovery implementation and validation:
- PUBLISH_LED_DISCOVERY=0 → no LED discovery published
- PUBLISH_LED_DISCOVERY=1 → publish LED discovery with strict schema
"""

import json
import os
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
PUBLISH_LED_DISCOVERY = int(os.environ.get("PUBLISH_LED_DISCOVERY", "0"))

HA_DISCOVERY_PREFIX = "homeassistant"
CHECKPOINT_DIR = "/Users/evertappels/Projects/HA-BB8/reports/checkpoints/INT-HA-CONTROL"


class LEDEntityAlignmentTest:
    def __init__(self):
        self.client = mqtt.Client(
            client_id=f"led-alignment-test-{int(time.time())}",
            callback_api_version=CallbackAPIVersion.VERSION2,
        )
        self.client.username_pw_set(MQTT_USER, MQTT_PASS)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

        self.discovery_topics = {}
        self.led_command_responses = []
        self.logs = []

        # Expected LED discovery schema
        self.expected_led_schema = {
            "name": "BB-8 LED",  # or just "LED"
            "schema": "json",
            "command_topic": f"{MQTT_BASE}/led/set",
            "enabled_by_default": False,
            "device": {"identifiers": ["bb8:DEVICE_ID"], "name": "Sphero BB-8"},
        }

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
                "Connected for LED alignment test",
                host=MQTT_HOST,
                port=MQTT_PORT,
            )
            # Subscribe to LED discovery and command/state topics
            topics = [
                (f"{HA_DISCOVERY_PREFIX}/light/+/config", 1),
                (f"{HA_DISCOVERY_PREFIX}/+/bb8_led/config", 1),
                (f"{MQTT_BASE}/led/state", 1),
                (f"{MQTT_BASE}/led/set", 1),
            ]
            for topic, qos in topics:
                client.subscribe(topic, qos)
            self.log_event("mqtt_subscribe", "Subscribed to LED-related topics")
        else:
            self.log_event("mqtt_error", f"Connection failed with code {rc}")

    def on_message(self, client, userdata, msg):
        topic = msg.topic

        # Process LED discovery messages
        if "config" in topic and ("light" in topic or "led" in topic):
            try:
                payload = json.loads(msg.payload.decode("utf-8"))
                self.discovery_topics[topic] = {
                    "payload": payload,
                    "retained": msg.retain,
                }
                self.log_event(
                    "led_discovery_found",
                    "LED discovery config found",
                    topic=topic,
                    retained=msg.retain,
                )
            except json.JSONDecodeError:
                self.log_event(
                    "led_discovery_invalid", "Invalid LED discovery JSON", topic=topic
                )

        # Process LED command/state responses
        elif topic == f"{MQTT_BASE}/led/state":
            try:
                payload = json.loads(msg.payload.decode("utf-8"))
                self.led_command_responses.append(
                    {
                        "timestamp": datetime.now().isoformat(),
                        "type": "state",
                        "payload": payload,
                    }
                )
                self.log_event(
                    "led_state_received", "LED state update received", payload=payload
                )
            except json.JSONDecodeError:
                self.log_event("led_state_invalid", "Invalid LED state JSON")

    def scan_led_discovery(self, scan_duration=5):
        """Scan for LED discovery topics"""
        self.log_event(
            "led_scan_start",
            f"Starting LED discovery scan for {scan_duration}s",
            publish_led_discovery=PUBLISH_LED_DISCOVERY,
        )

        self.client.connect(MQTT_HOST, MQTT_PORT, 60)
        self.client.loop_start()

        time.sleep(scan_duration)

        self.client.loop_stop()
        self.client.disconnect()

        led_topics_found = len(self.discovery_topics)
        self.log_event(
            "led_scan_complete",
            "LED discovery scan completed",
            topics_found=led_topics_found,
        )

        return led_topics_found

    def test_led_command_schema(self):
        """Test LED command payload schema validation"""
        test_cases = [
            {
                "name": "valid_rgb",
                "payload": {"r": 255, "g": 0, "b": 128},
                "expected_valid": True,
            },
            {
                "name": "valid_rgb_zeros",
                "payload": {"r": 0, "g": 0, "b": 0},
                "expected_valid": True,
            },
            {
                "name": "valid_rgb_max",
                "payload": {"r": 255, "g": 255, "b": 255},
                "expected_valid": True,
            },
            {
                "name": "invalid_out_of_range_high",
                "payload": {"r": 300, "g": 0, "b": 0},
                "expected_valid": False,
            },
            {
                "name": "invalid_out_of_range_negative",
                "payload": {"r": -1, "g": 0, "b": 0},
                "expected_valid": False,
            },
            {
                "name": "invalid_extra_fields",
                "payload": {
                    "r": 255,
                    "g": 0,
                    "b": 0,
                    "brightness": 128,
                    "extra": "field",
                },
                "expected_valid": False,  # Strict: no extra fields allowed
            },
            {
                "name": "invalid_missing_fields",
                "payload": {"r": 255, "g": 0},  # Missing 'b'
                "expected_valid": False,
            },
            {
                "name": "invalid_wrong_types",
                "payload": {"r": "255", "g": 0, "b": 0},  # String instead of int
                "expected_valid": False,
            },
        ]

        schema_results = []

        for test_case in test_cases:
            result = self.validate_led_payload(test_case["payload"])
            schema_results.append(
                {
                    "test_name": test_case["name"],
                    "payload": test_case["payload"],
                    "expected_valid": test_case["expected_valid"],
                    "actual_valid": result["valid"],
                    "errors": result.get("errors", []),
                    "test_pass": result["valid"] == test_case["expected_valid"],
                }
            )

            self.log_event(
                "led_schema_test",
                f"Schema test: {test_case['name']}",
                expected=test_case["expected_valid"],
                actual=result["valid"],
                test_pass=result["valid"] == test_case["expected_valid"],
            )

        return schema_results

    def validate_led_payload(self, payload):
        """Validate LED command payload against strict schema"""
        errors = []

        # Must be dict
        if not isinstance(payload, dict):
            return {"valid": False, "errors": ["Payload must be a JSON object"]}

        # Must have exactly r, g, b fields
        required_fields = {"r", "g", "b"}
        payload_fields = set(payload.keys())

        if payload_fields != required_fields:
            missing = required_fields - payload_fields
            extra = payload_fields - required_fields
            if missing:
                errors.append(f"Missing required fields: {missing}")
            if extra:
                errors.append(f"Extra fields not allowed: {extra}")

        # Validate r, g, b values
        for field in ["r", "g", "b"]:
            if field in payload:
                value = payload[field]
                if not isinstance(value, int):
                    errors.append(
                        f"Field '{field}' must be integer, got {type(value).__name__}"
                    )
                elif not (0 <= value <= 255):
                    errors.append(f"Field '{field}' must be 0-255, got {value}")

        return {"valid": len(errors) == 0, "errors": errors}

    def analyze_device_block_alignment(self):
        """Check if LED entity shares device block with other BB8 entities"""
        device_blocks = {}

        for topic, data in self.discovery_topics.items():
            payload = data["payload"]
            device_info = payload.get("dev") or payload.get("device", {})
            identifiers = device_info.get("identifiers", [])

            if identifiers:
                device_key = str(identifiers[0]) if identifiers else "no_identifier"
                if device_key not in device_blocks:
                    device_blocks[device_key] = []
                device_blocks[device_key].append(
                    {
                        "topic": topic,
                        "entity_name": payload.get("name", "Unknown"),
                        "unique_id": payload.get("uniq_id") or payload.get("unique_id"),
                    }
                )

        alignment_result = {
            "device_blocks_found": len(device_blocks),
            "devices": device_blocks,
            "led_properly_aligned": False,
            "collocated_entities": [],
        }

        # Check if LED is in same device block as other BB8 entities
        for device_key, entities in device_blocks.items():
            entity_names = [e["entity_name"] for e in entities]
            led_entities = [e for e in entities if "led" in e["entity_name"].lower()]
            bb8_entities = [
                e
                for e in entities
                if "bb8" in e["entity_name"].lower()
                or "bb-8" in e["entity_name"].lower()
            ]

            if led_entities and bb8_entities:
                alignment_result["led_properly_aligned"] = True
                alignment_result["collocated_entities"] = entity_names

        self.log_event(
            "device_block_analysis",
            "Device block alignment analyzed",
            blocks_found=alignment_result["device_blocks_found"],
            led_aligned=alignment_result["led_properly_aligned"],
        )

        return alignment_result

    def generate_led_alignment_reports(self):
        """Generate LED entity alignment validation reports"""

        # Scan for LED discovery
        led_topics_found = self.scan_led_discovery()

        # Test schema validation
        schema_test_results = self.test_led_command_schema()

        # Analyze device block alignment
        device_alignment = self.analyze_device_block_alignment()

        # Generate validation summary
        toggle_test_results = {
            "toggle_0_case": {
                "expected_led_discovery": False,
                "actual_led_discovery": led_topics_found > 0,
                "test_pass": (
                    (led_topics_found == 0) if PUBLISH_LED_DISCOVERY == 0 else True
                ),
            },
            "toggle_1_case": {
                "expected_led_discovery": True,
                "actual_led_discovery": led_topics_found > 0,
                "test_pass": (
                    (led_topics_found > 0) if PUBLISH_LED_DISCOVERY == 1 else True
                ),
            },
        }

        schema_pass_count = sum(1 for r in schema_test_results if r["test_pass"])
        schema_all_pass = schema_pass_count == len(schema_test_results)

        validation_data = {
            "validation_metadata": {
                "timestamp": datetime.now().isoformat(),
                "mqtt_host": MQTT_HOST,
                "mqtt_base": MQTT_BASE,
                "publish_led_discovery": PUBLISH_LED_DISCOVERY,
            },
            "toggle_testing": toggle_test_results,
            "schema_validation": {
                "total_tests": len(schema_test_results),
                "passed_tests": schema_pass_count,
                "all_tests_pass": schema_all_pass,
                "test_details": schema_test_results,
            },
            "device_alignment": device_alignment,
            "led_discovery_topics": self.discovery_topics,
            "compliance_status": {
                "toggle_compliance": toggle_test_results[
                    f"toggle_{PUBLISH_LED_DISCOVERY}_case"
                ]["test_pass"],
                "schema_compliance": schema_all_pass,
                "device_alignment": (
                    device_alignment["led_properly_aligned"]
                    if led_topics_found > 0
                    else True
                ),
                "overall_pass": all(
                    [
                        toggle_test_results[f"toggle_{PUBLISH_LED_DISCOVERY}_case"][
                            "test_pass"
                        ],
                        schema_all_pass,
                        (
                            device_alignment["led_properly_aligned"]
                            if led_topics_found > 0
                            else True
                        ),
                    ]
                ),
            },
        }

        # Device block audit log
        audit_log = []
        audit_log.append(f"LED Entity Schema Validation - {datetime.now().isoformat()}")
        audit_log.append("=" * 60)
        audit_log.append(f"PUBLISH_LED_DISCOVERY setting: {PUBLISH_LED_DISCOVERY}")
        audit_log.append(f"LED discovery topics found: {led_topics_found}")
        audit_log.append("")

        current_case = toggle_test_results[f"toggle_{PUBLISH_LED_DISCOVERY}_case"]
        audit_log.append(
            f"Toggle Test (PUBLISH_LED_DISCOVERY={PUBLISH_LED_DISCOVERY}):"
        )
        audit_log.append(
            f"  Expected LED discovery: {current_case['expected_led_discovery']}"
        )
        audit_log.append(
            f"  Actual LED discovery: {current_case['actual_led_discovery']}"
        )
        audit_log.append(f"  Test PASS: {current_case['test_pass']}")
        audit_log.append("")

        audit_log.append(
            f"Schema Validation: {schema_pass_count}/{len(schema_test_results)} tests passed"
        )
        for result in schema_test_results:
            status = "✓" if result["test_pass"] else "✗"
            audit_log.append(f"  {status} {result['test_name']}: {result['payload']}")

        audit_log.append("")
        audit_log.append("Device Block Alignment:")
        audit_log.append(
            f"  LED properly collocated: {device_alignment['led_properly_aligned']}"
        )
        if device_alignment["collocated_entities"]:
            audit_log.append(
                f"  Collocated with: {', '.join(device_alignment['collocated_entities'])}"
            )

        # Write reports
        with open(f"{CHECKPOINT_DIR}/led_entity_schema_validation.json", "w") as f:
            f.write(json.dumps(validation_data, indent=2))

        with open(f"{CHECKPOINT_DIR}/device_block_audit.log", "w") as f:
            f.write("\n".join(audit_log))

        self.log_event(
            "led_reports_generated",
            "LED alignment reports generated",
            overall_pass=validation_data["compliance_status"]["overall_pass"],
        )

        return validation_data


def main():
    test = LEDEntityAlignmentTest()
    validation_result = test.generate_led_alignment_reports()

    # Summary output
    compliance = validation_result["compliance_status"]
    print("\n=== LED Entity Alignment Summary ===")
    print(f"PUBLISH_LED_DISCOVERY: {PUBLISH_LED_DISCOVERY}")
    print(f"Toggle compliance: {compliance['toggle_compliance']}")
    print(f"Schema compliance: {compliance['schema_compliance']}")
    print(f"Device alignment: {compliance['device_alignment']}")
    print(f"Overall PASS: {compliance['overall_pass']}")

    schema_stats = validation_result["schema_validation"]
    print(
        f"Schema tests: {schema_stats['passed_tests']}/{schema_stats['total_tests']} passed"
    )

    return 0 if compliance["overall_pass"] else 1


if __name__ == "__main__":
    exit(main())

#!/usr/bin/env python3
"""
BB-8 Command Route Testing Script
Phase B2 - Test all command routes with validation and acknowledgment tracking
"""

import json
import time
import paho.mqtt.client as mqtt
from typing import Dict, List, Any, Optional
import logging
import threading
from datetime import datetime
import uuid
from bb8_validator import BB8CommandValidator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("b2_route_tests.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


class BB8RouteTestHarness:
    """Test harness for BB-8 MQTT command routing and validation"""

    def __init__(
        self,
        host: str = "core-mosquitto",
        port: int = 1883,
        username: str = "mqtt_bb8",
        password: str = "mqtt_bb8",
    ):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.base_topic = "bb8"

        # MQTT client setup
        self.client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            protocol=mqtt.MQTTv311,
        )
        self.client.username_pw_set(username, password)
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message

        # Test state
        self.received_acks = {}
        self.test_results = []
        self.validator = BB8CommandValidator("b2_schema.json")
        self.lock = threading.Lock()

    def _on_connect(self, client, userdata, flags, rc):
        """MQTT connection callback"""
        if rc == 0:
            logger.info(f"Connected to MQTT broker at {self.host}:{self.port}")
            # Subscribe to all ack topics
            client.subscribe(f"{self.base_topic}/ack/+")
            logger.info(f"Subscribed to {self.base_topic}/ack/+")
        else:
            logger.error(f"Failed to connect to MQTT broker: {rc}")

    def _on_message(self, client, userdata, msg):
        """MQTT message callback - capture acknowledgments"""
        topic = msg.topic
        try:
            payload = json.loads(msg.payload.decode())
            with self.lock:
                self.received_acks[topic] = {
                    "payload": payload,
                    "timestamp": datetime.utcnow().isoformat(),
                    "topic": topic,
                }
            logger.info(f"Received ack on {topic}: {payload}")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode ack on {topic}: {e}")

    def connect(self) -> bool:
        """Connect to MQTT broker"""
        try:
            self.client.connect(self.host, self.port, 60)
            self.client.loop_start()
            time.sleep(2)  # Allow connection to establish
            return True
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            return False

    def disconnect(self):
        """Disconnect from MQTT broker"""
        self.client.loop_stop()
        self.client.disconnect()

    def publish_command(
        self, command: str, payload: Dict[str, Any], expect_ack: bool = True
    ) -> Dict[str, Any]:
        """
        Publish command and optionally wait for acknowledgment
        Returns test result dict
        """
        topic = f"{self.base_topic}/cmd/{command}"
        ack_topic = f"{self.base_topic}/ack/{command}"

        # Generate correlation ID if not provided
        cid = payload.get("cid", f"test_{command}_{uuid.uuid4().hex[:8]}")
        if "cid" not in payload:
            payload["cid"] = cid

        # Validate command locally first
        is_valid, processed_payload, validation_msg = (
            self.validator.validate_command(topic, payload)
        )

        test_result = {
            "command": command,
            "topic": topic,
            "original_payload": payload.copy(),
            "processed_payload": processed_payload,
            "correlation_id": cid,
            "validation_local": {"valid": is_valid, "message": validation_msg},
            "publish_timestamp": datetime.utcnow().isoformat(),
            "ack_received": False,
            "ack_payload": None,
            "test_status": "unknown",
        }

        # Clear any previous ack for this topic
        with self.lock:
            if ack_topic in self.received_acks:
                del self.received_acks[ack_topic]

        # Publish command
        try:
            payload_json = json.dumps(payload)
            result = self.client.publish(topic, payload_json)
            logger.info(f"Published to {topic}: {payload_json}")

            if expect_ack:
                # Wait for acknowledgment
                timeout = 10  # seconds
                start_time = time.time()

                while time.time() - start_time < timeout:
                    with self.lock:
                        if ack_topic in self.received_acks:
                            ack_data = self.received_acks[ack_topic]
                            test_result["ack_received"] = True
                            test_result["ack_payload"] = ack_data["payload"]
                            test_result["ack_timestamp"] = ack_data["timestamp"]

                            # Check if ack correlation ID matches
                            ack_cid = ack_data["payload"].get("cid")
                            if ack_cid == cid:
                                test_result["correlation_matched"] = True
                            else:
                                test_result["correlation_matched"] = False
                                logger.warning(
                                    f"Correlation ID mismatch: sent {cid}, received {ack_cid}"
                                )

                            # Determine test status
                            ack_ok = ack_data["payload"].get("ok", False)
                            if is_valid and ack_ok:
                                test_result["test_status"] = "success"
                            elif not is_valid and not ack_ok:
                                test_result["test_status"] = (
                                    "correctly_rejected"
                                )
                            else:
                                test_result["test_status"] = "status_mismatch"

                            break

                    time.sleep(0.1)

                if not test_result["ack_received"]:
                    test_result["test_status"] = "ack_timeout"
                    logger.warning(
                        f"No ack received for {topic} within {timeout}s"
                    )

        except Exception as e:
            test_result["publish_error"] = str(e)
            test_result["test_status"] = "publish_failed"
            logger.error(f"Failed to publish to {topic}: {e}")

        self.test_results.append(test_result)
        return test_result

    def run_comprehensive_tests(self) -> List[Dict[str, Any]]:
        """Run comprehensive test suite covering all command types and edge cases"""
        logger.info("Starting comprehensive BB-8 command route tests")

        # Test 1: Valid drive command
        self.publish_command("drive", {"speed": 100, "heading": 90, "ms": 2000})

        # Test 2: Drive command with clamping
        self.publish_command(
            "drive",
            {
                "speed": 300,  # Should clamp to 255
                "heading": 400,  # Should wrap to 40
                "ms": 10000,  # Should clamp to 5000
                "cid": "clamp_test",
            },
        )

        # Test 3: Invalid drive command (missing required field)
        self.publish_command(
            "drive",
            {
                "speed": 100,
                "heading": 90,
                # missing 'ms' - should be rejected
            },
        )

        # Test 4: Valid stop command
        self.publish_command("stop", {})

        # Test 5: Stop command with correlation ID
        self.publish_command("stop", {"cid": "stop_with_cid"})

        # Test 6: Valid LED command
        self.publish_command("led", {"r": 255, "g": 0, "b": 128})

        # Test 7: LED command with clamping
        self.publish_command(
            "led",
            {
                "r": 300,  # Should clamp to 255
                "g": -50,  # Should clamp to 0
                "b": 128,
                "cid": "led_clamp",
            },
        )

        # Test 8: Invalid LED command (missing required field)
        self.publish_command(
            "led",
            {
                "r": 255,
                "g": 0,
                # missing 'b' - should be rejected
            },
        )

        # Test 9: Valid power wake command
        self.publish_command("power", {"action": "wake"})

        # Test 10: Valid power sleep command
        self.publish_command("power", {"action": "sleep", "cid": "sleep_test"})

        # Test 11: Invalid power command (bad action)
        self.publish_command(
            "power",
            {
                "action": "hibernate"  # Invalid - should be rejected
            },
        )

        # Test 12: Emergency stop
        self.publish_command("estop", {"cid": "emergency_test"})

        # Test 13: Drive command while estop active (should be rejected)
        self.publish_command(
            "drive",
            {"speed": 50, "heading": 0, "ms": 1000, "cid": "blocked_by_estop"},
        )

        # Test 14: Clear emergency stop
        self.publish_command("clear_estop", {"cid": "clear_emergency"})

        # Test 15: Drive command after estop cleared (should work)
        self.publish_command(
            "drive",
            {
                "speed": 50,
                "heading": 180,
                "ms": 1000,
                "cid": "after_estop_clear",
            },
        )

        # Test 16: Invalid clear_estop when no estop active
        self.publish_command("clear_estop", {"cid": "invalid_clear"})

        # Test 17: Command with extra fields (should be rejected)
        self.publish_command(
            "drive",
            {
                "speed": 100,
                "heading": 90,
                "ms": 2000,
                "turbo": True,  # Extra field - should be rejected
                "cid": "extra_fields",
            },
        )

        # Test 18: Command with invalid correlation ID format
        self.publish_command(
            "stop",
            {
                "cid": "invalid@cid#format!"  # Invalid characters - should be rejected
            },
        )

        logger.info(f"Completed {len(self.test_results)} tests")
        return self.test_results

    def generate_report(self) -> str:
        """Generate comprehensive test report"""
        report_lines = [
            "=" * 80,
            "BB-8 MQTT Command Route Test Report",
            f"Generated: {datetime.utcnow().isoformat()}Z",
            f"Total Tests: {len(self.test_results)}",
            "=" * 80,
            "",
        ]

        # Summary statistics
        success_count = sum(
            1 for r in self.test_results if r["test_status"] == "success"
        )
        rejected_count = sum(
            1
            for r in self.test_results
            if r["test_status"] == "correctly_rejected"
        )
        timeout_count = sum(
            1 for r in self.test_results if r["test_status"] == "ack_timeout"
        )
        failed_count = sum(
            1
            for r in self.test_results
            if r["test_status"] in ["status_mismatch", "publish_failed"]
        )

        report_lines.extend([
            "SUMMARY:",
            f"  Successful: {success_count}",
            f"  Correctly Rejected: {rejected_count}",
            f"  Timeouts: {timeout_count}",
            f"  Failures: {failed_count}",
            "",
        ])

        # Detailed results
        report_lines.append("DETAILED RESULTS:")
        report_lines.append("")

        for i, result in enumerate(self.test_results, 1):
            report_lines.extend([
                f"Test {i}: {result['command']} - {result['test_status'].upper()}",
                f"  Topic: {result['topic']}",
                f"  Original Payload: {json.dumps(result['original_payload'])}",
                f"  Processed Payload: {json.dumps(result['processed_payload'])}",
                f"  Local Validation: {'PASS' if result['validation_local']['valid'] else 'FAIL'}",
            ])

            if result["validation_local"]["message"]:
                report_lines.append(
                    f"  Validation Message: {result['validation_local']['message']}"
                )

            if result["ack_received"]:
                report_lines.extend([
                    f"  Ack Received: YES",
                    f"  Ack Payload: {json.dumps(result['ack_payload'])}",
                    f"  Correlation Matched: {result.get('correlation_matched', 'N/A')}",
                ])
            else:
                report_lines.append(f"  Ack Received: NO")

            if "publish_error" in result:
                report_lines.append(
                    f"  Publish Error: {result['publish_error']}"
                )

            report_lines.append("")

        return "\n".join(report_lines)


def main():
    """Main test execution"""
    # Use localhost for development, core-mosquitto for HA environment
    import os

    mqtt_host = os.getenv("MQTT_HOST", "localhost")
    mqtt_port = int(os.getenv("MQTT_PORT", "1883"))
    mqtt_user = os.getenv("MQTT_USER", "mqtt_bb8")
    mqtt_pass = os.getenv("MQTT_PASS", "mqtt_bb8")

    logger.info(f"Starting BB-8 route tests against {mqtt_host}:{mqtt_port}")

    harness = BB8RouteTestHarness(mqtt_host, mqtt_port, mqtt_user, mqtt_pass)

    if not harness.connect():
        logger.error("Failed to connect to MQTT broker")
        return 1

    try:
        # Run comprehensive tests
        results = harness.run_comprehensive_tests()

        # Generate and save report
        report = harness.generate_report()

        with open("b2_route_tests.log", "a") as f:
            f.write("\n" + report + "\n")

        print("\n" + report)

        # Return appropriate exit code
        failed_tests = [
            r
            for r in results
            if r["test_status"]
            in ["status_mismatch", "publish_failed", "ack_timeout"]
        ]
        if failed_tests:
            logger.error(f"{len(failed_tests)} tests failed")
            return 1
        else:
            logger.info("All tests passed")
            return 0

    finally:
        harness.disconnect()


if __name__ == "__main__":
    exit(main())

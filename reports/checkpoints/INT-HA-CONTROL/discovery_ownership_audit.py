#!/usr/bin/env python3
"""
INT-HA-CONTROL P2 Discovery Ownership Audit
Prevents and detects single-owner discovery conflicts by auditing retained HA discovery topics
"""

import hashlib
import json
import os
import time
from collections import defaultdict
from datetime import datetime

import paho.mqtt.client as mqtt
from paho.mqtt.client import CallbackAPIVersion

# Configuration
MQTT_HOST = os.environ.get("MQTT_HOST", "192.168.0.129")
MQTT_PORT = int(os.environ.get("MQTT_PORT", "1883"))
MQTT_USER = os.environ.get("MQTT_USERNAME", "mqtt_bb8")
MQTT_PASS = os.environ.get("MQTT_PASSWORD", "mqtt_bb8")
MQTT_BASE = os.environ.get("MQTT_BASE", "bb8")

HA_DISCOVERY_PREFIX = "homeassistant"
CHECKPOINT_DIR = "/Users/evertappels/Projects/HA-BB8/reports/checkpoints/INT-HA-CONTROL"


class DiscoveryOwnershipAudit:
    def __init__(self):
        self.client = mqtt.Client(
            client_id=f"discovery-audit-{int(time.time())}",
            callback_api_version=CallbackAPIVersion.VERSION2,
        )
        self.client.username_pw_set(MQTT_USER, MQTT_PASS)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

        # Discovery data storage
        self.discovery_topics = {}
        self.device_identifiers = defaultdict(list)
        self.unique_ids = defaultdict(list)
        self.logs = []
        self.scan_complete = False

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
                "Connected for discovery audit",
                host=MQTT_HOST,
                port=MQTT_PORT,
            )
            # Subscribe to all HA discovery topics
            client.subscribe(f"{HA_DISCOVERY_PREFIX}/+/+/config", qos=1)
            client.subscribe(
                f"{HA_DISCOVERY_PREFIX}/+/+/+/config", qos=1
            )  # deeper nesting
            self.log_event("mqtt_subscribe", "Subscribed to discovery topics")
        else:
            self.log_event("mqtt_error", f"Connection failed with code {rc}")

    def on_message(self, client, userdata, msg):
        try:
            # Only process retained messages for ownership audit
            if not msg.retain:
                return

            payload = json.loads(msg.payload.decode("utf-8"))
            topic = msg.topic

            self.discovery_topics[topic] = {
                "payload": payload,
                "payload_hash": hashlib.md5(msg.payload).hexdigest(),
                "retained": msg.retain,
                "size_bytes": len(msg.payload),
            }

            # Extract ownership information
            unique_id = payload.get("uniq_id") or payload.get("unique_id")
            device_info = payload.get("dev") or payload.get("device", {})
            device_identifiers = device_info.get("identifiers", [])
            device_name = device_info.get("name", "Unknown")

            if unique_id:
                self.unique_ids[unique_id].append(
                    {
                        "topic": topic,
                        "device_name": device_name,
                        "device_identifiers": device_identifiers,
                    }
                )

            if device_identifiers:
                for identifier in device_identifiers:
                    self.device_identifiers[str(identifier)].append(
                        {
                            "topic": topic,
                            "unique_id": unique_id,
                            "device_name": device_name,
                        }
                    )

            self.log_event(
                "discovery_found",
                "Discovery config found",
                topic=topic,
                unique_id=unique_id,
                device_name=device_name,
                identifiers_count=len(device_identifiers),
            )

        except json.JSONDecodeError:
            self.log_event(
                "discovery_invalid", "Invalid JSON in discovery topic", topic=msg.topic
            )
        except Exception as e:
            self.log_event(
                "discovery_error", f"Error processing discovery: {e}", topic=msg.topic
            )

    def scan_discovery_topics(self, scan_duration=10):
        """Scan for retained discovery topics for specified duration"""
        self.log_event(
            "scan_start", "Starting discovery topic scan", duration_sec=scan_duration
        )

        self.client.connect(MQTT_HOST, MQTT_PORT, 60)
        self.client.loop_start()

        # Let messages accumulate
        time.sleep(scan_duration)

        self.client.loop_stop()
        self.client.disconnect()

        self.scan_complete = True
        self.log_event(
            "scan_complete",
            "Discovery scan completed",
            topics_found=len(self.discovery_topics),
        )

    def analyze_ownership(self):
        """Analyze discovery topics for ownership conflicts"""
        analysis = {
            "duplicate_unique_ids": {},
            "conflicting_device_blocks": {},
            "bb8_entities": {},
            "total_topics": len(self.discovery_topics),
            "bb8_topic_count": 0,
            "duplicate_count": 0,
        }

        # Check for duplicate unique_ids
        for uid, occurrences in self.unique_ids.items():
            if len(occurrences) > 1:
                analysis["duplicate_unique_ids"][uid] = occurrences
                analysis["duplicate_count"] += len(occurrences) - 1

        # Check for conflicting device blocks with same identifiers
        for identifier, occurrences in self.device_identifiers.items():
            device_names = set(occ["device_name"] for occ in occurrences)
            if len(device_names) > 1:
                analysis["conflicting_device_blocks"][identifier] = {
                    "device_names": list(device_names),
                    "occurrences": occurrences,
                }

        # Identify BB8-related entities
        bb8_related = [
            topic
            for topic in self.discovery_topics.keys()
            if MQTT_BASE in topic.lower()
            or "bb8" in topic.lower()
            or "bb-8" in topic.lower()
        ]

        for topic in bb8_related:
            analysis["bb8_entities"][topic] = self.discovery_topics[topic]
            analysis["bb8_topic_count"] += 1

        return analysis

    def generate_ownership_reports(self):
        """Generate human and machine readable ownership reports"""
        if not self.scan_complete:
            raise RuntimeError("Must run scan_discovery_topics() first")

        analysis = self.analyze_ownership()

        # Human readable report
        human_report = []
        human_report.append(f"Discovery Ownership Check - {datetime.now().isoformat()}")
        human_report.append("=" * 60)
        human_report.append(f"Total discovery topics found: {analysis['total_topics']}")
        human_report.append(f"BB8-related topics: {analysis['bb8_topic_count']}")
        human_report.append(f"Duplicate count: {analysis['duplicate_count']}")
        human_report.append("")

        if analysis["duplicate_count"] == 0:
            human_report.append("✓ OK: single owner - No duplicate unique_ids detected")
        else:
            human_report.append("✗ DUPLICATES DETECTED:")
            for uid, occurrences in analysis["duplicate_unique_ids"].items():
                human_report.append(
                    f"  Unique ID '{uid}' appears in {len(occurrences)} topics:"
                )
                for occ in occurrences:
                    human_report.append(f"    - {occ['topic']} ({occ['device_name']})")

        if analysis["conflicting_device_blocks"]:
            human_report.append("")
            human_report.append("Device Block Conflicts:")
            for identifier, conflict in analysis["conflicting_device_blocks"].items():
                human_report.append(
                    f"  Identifier '{identifier}' has conflicting device names:"
                )
                for name in conflict["device_names"]:
                    human_report.append(f"    - {name}")

        human_report.append("")
        human_report.append("BB8 Entities:")
        for topic, data in analysis["bb8_entities"].items():
            payload = data["payload"]
            unique_id = payload.get("uniq_id", "N/A")
            name = payload.get("name", "N/A")
            human_report.append(f"  {topic}")
            human_report.append(f"    Name: {name}, Unique ID: {unique_id}")

        # Machine readable audit
        audit_data = {
            "audit_metadata": {
                "timestamp": datetime.now().isoformat(),
                "mqtt_host": MQTT_HOST,
                "mqtt_base": MQTT_BASE,
                "scan_duration": 10,
                "total_topics_scanned": analysis["total_topics"],
            },
            "ownership_analysis": analysis,
            "topic_fingerprints": {
                topic: {
                    "hash": data["payload_hash"],
                    "size": data["size_bytes"],
                    "retained": data["retained"],
                }
                for topic, data in self.discovery_topics.items()
            },
            "compliance_status": {
                "single_owner": analysis["duplicate_count"] == 0,
                "bb8_entities_found": analysis["bb8_topic_count"],
                "conflicts_detected": len(analysis["conflicting_device_blocks"]),
                "overall_pass": analysis["duplicate_count"] == 0
                and len(analysis["conflicting_device_blocks"]) == 0,
            },
        }

        # Write reports to canonical location
        from pathlib import Path

        repo_root = Path(__file__).parent.parent.parent.parent
        reports_dir = repo_root / "reports"
        reports_dir.mkdir(exist_ok=True)

        with open(reports_dir / "discovery_ownership_check.txt", "w") as f:
            f.write("\n".join(human_report))

        with open(reports_dir / "entity_audit_results.json", "w") as f:
            f.write(json.dumps(audit_data, indent=2))

        self.log_event(
            "reports_generated",
            "Ownership reports generated",
            duplicates=analysis["duplicate_count"],
            conflicts=len(analysis["conflicting_device_blocks"]),
            overall_pass=audit_data["compliance_status"]["overall_pass"],
        )

        return audit_data


def main():
    audit = DiscoveryOwnershipAudit()

    # Perform discovery scan
    audit.scan_discovery_topics(scan_duration=10)

    # Generate reports
    audit_result = audit.generate_ownership_reports()

    # Summary output
    compliance = audit_result["compliance_status"]
    print("\n=== Discovery Ownership Audit Summary ===")
    print(f"Topics scanned: {audit_result['audit_metadata']['total_topics_scanned']}")
    print(f"BB8 entities: {compliance['bb8_entities_found']}")
    print(
        f"Duplicates detected: {audit_result['ownership_analysis']['duplicate_count']}"
    )
    print(f"Conflicts detected: {compliance['conflicts_detected']}")
    print(f"Single owner compliance: {compliance['single_owner']}")
    print(f"Overall PASS: {compliance['overall_pass']}")

    return 0 if compliance["overall_pass"] else 1


if __name__ == "__main__":
    exit(main())

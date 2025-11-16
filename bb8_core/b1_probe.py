"""
B1 Probe Surface for BB-8 Health Monitoring

Handles bb8/cmd/power subscription and publishes health metrics
for B1 gate validation.
"""

from __future__ import annotations

import asyncio
import json
import os
import time
from typing import Any

from .addon_config import load_config
from .ble_session import BleSession
from .logging_setup import logger


class B1ProbeHandler:
    """Handler for B1 probe commands and health publishing."""

    def __init__(self, facade: Any, ble_session: BleSession):
        """Initialize B1 probe handler."""
        self.facade = facade
        self.ble_session = ble_session
        self._health_metrics = {
            "connect_ok": False,
            "reconnect_attempts": 0,
            "battery_pct": 75,
            "ts": None,
            "mean_connect_ms": 0.0,
            "last_ok_ts": None,
            "last_error": None,
        }

    def setup_subscriptions(self, client, base_topic: str) -> None:
        """Set up MQTT subscriptions for B1 probe."""
        power_topic = f"{base_topic}/cmd/power"

        def handle_power_cmd(_client, _userdata, msg):
            try:
                payload = (msg.payload or b"").decode("utf-8").strip()
                if payload.startswith("{"):
                    data = json.loads(payload)
                else:
                    data = {"action": payload}

                action = data.get("action", "").lower()
                logger.info(
                    {
                        "event": "b1_power_cmd_received",
                        "action": action,
                        "payload": payload,
                    }
                )

                if action == "wake":
                    asyncio.create_task(self._handle_wake())
                elif action == "sleep":
                    asyncio.create_task(self._handle_sleep())
                else:
                    logger.warning(
                        {
                            "event": "b1_power_cmd_invalid",
                            "action": action,
                        }
                    )

            except Exception as e:
                logger.error({"event": "b1_power_cmd_error", "error": str(e)})

        client.message_callback_add(power_topic, handle_power_cmd)
        client.subscribe(power_topic, qos=1)

        logger.info(
            {
                "event": "b1_probe_subscriptions_setup",
                "power_topic": power_topic,
            }
        )

    async def _handle_wake(self) -> None:
        """Handle wake command."""
        try:
            connect_start = time.time()

            if not self.ble_session.is_connected():
                await self.ble_session.connect()

            await self.ble_session.wake()

            connect_time = (time.time() - connect_start) * 1000

            # Update metrics
            self._health_metrics.update(
                {
                    "connect_ok": True,
                    "last_ok_ts": time.time(),
                    "mean_connect_ms": connect_time,
                }
            )

            # Get battery if possible
            try:
                battery = await self.ble_session.battery()
                self._health_metrics["battery_pct"] = battery
            except Exception:
                pass

            await self._publish_health()

            logger.info(
                {
                    "event": "b1_wake_success",
                    "connect_time_ms": connect_time,
                }
            )

        except Exception as e:
            self._health_metrics.update(
                {
                    "connect_ok": False,
                    "last_error": str(e),
                    "reconnect_attempts": (
                        self._health_metrics["reconnect_attempts"] + 1
                    ),
                }
            )

            await self._publish_health()

            logger.error({"event": "b1_wake_error", "error": str(e)})

    async def _handle_sleep(self) -> None:
        """Handle sleep command."""
        try:
            if self.ble_session.is_connected():
                await self.ble_session.sleep()

            self._health_metrics["connect_ok"] = False
            await self._publish_health()

            logger.info({"event": "b1_sleep_success"})

        except Exception as e:
            logger.error({"event": "b1_sleep_error", "error": str(e)})

    async def _publish_health(self) -> None:
        """Publish health metrics to MQTT and file."""
        try:
            cfg, _ = load_config()

            # Update timestamp
            self._health_metrics["ts"] = time.strftime(
                "%Y-%m-%dT%H:%M:%SZ", time.gmtime()
            )

            # Publish to MQTT
            try:
                facade_mqtt = getattr(self.facade, "_mqtt", {})
                if facade_mqtt.get("client"):
                    client = facade_mqtt["client"]
                    base = cfg.get("MQTT_BASE", "bb8")
                    topic = f"{base}/status/health"

                    payload = json.dumps(self._health_metrics, separators=(",", ":"))
                    client.publish(topic, payload=payload, qos=1, retain=True)

                    logger.debug(
                        {
                            "event": "b1_health_mqtt_published",
                            "topic": topic,
                        }
                    )
            except Exception as e:
                logger.debug({"event": "b1_health_mqtt_error", "error": str(e)})

            # Write health file for B1 evidence
            await self._write_health_file()

        except Exception as e:
            logger.error({"event": "b1_publish_health_error", "error": str(e)})

    async def _write_health_file(self) -> None:
        """Write health metrics to file for B1 evidence."""
        try:
            # Ensure checkpoint directory exists
            checkpoint_dir = (
                "/Users/evertappels/actions-runner/Projects/HA-BB8/"
                "reports/checkpoints/BB8-FUNC"
            )
            os.makedirs(checkpoint_dir, exist_ok=True)

            health_file = os.path.join(checkpoint_dir, "b1_ble_health.json")

            with open(health_file, "w") as f:
                json.dump(self._health_metrics, f, indent=2)

            logger.debug(
                {
                    "event": "b1_health_file_written",
                    "path": health_file,
                }
            )

        except Exception as e:
            logger.error({"event": "b1_health_file_error", "error": str(e)})

    def get_metrics(self) -> dict[str, Any]:
        """Get current health metrics."""
        return self._health_metrics.copy()

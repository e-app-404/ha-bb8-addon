from __future__ import annotations

import json
import os
import threading
import time
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from .logging_setup import logger

if TYPE_CHECKING:
    pass

# The environment variable "MQTT_BASE" should be set to the base topic for MQTT telemetry,
# MQTT retain is set to False by policy: telemetry messages represent transient state and should not be stored by the broker.
# Consumers will only receive telemetry updates when they are actively subscribed and connected; they will not receive old messages on (re)subscription.
RET = False
TELEMETRY_BASE = os.environ.get("MQTT_BASE", "bb8") + "/telemetry"
RET = False  # retain=false by policy


def _now() -> int:
    return int(time.time())


def publish_metric(mqtt, name: str, data: dict[str, Any]) -> None:
    topic = f"{TELEMETRY_BASE}/{name}"
    payload = json.dumps({**data, "ts": _now()})
    mqtt.publish(topic, payload, qos=0, retain=RET)


def echo_roundtrip(mqtt, ms: int, outcome: str) -> None:
    publish_metric(mqtt, "echo_roundtrip", {"ms": ms, "outcome": outcome})


def ble_connect_attempt(mqtt, try_no: int, backoff_s: float) -> None:
    publish_metric(mqtt, "ble_connect_attempt", {"try": try_no, "backoff_s": backoff_s})


def led_discovery(mqtt, unique_id: str, duplicates: int) -> None:
    publish_metric(
        mqtt, "led_discovery", {"unique_id": unique_id, "duplicates": duplicates}
    )


class Telemetry:
    def __init__(
        self,
        bridge,
        interval_s: int = 20,
        publish_presence: Callable[[bool], None] | None = None,
        publish_rssi: Callable[[int], None] | None = None,
        sleep_interval: float = 1.0,
    ):
        self.bridge = bridge
        self.interval_s = interval_s
        self.sleep_interval = sleep_interval
        self._stop = threading.Event()
        self._t: threading.Thread | None = None
        self._cb_presence = publish_presence
        self._cb_rssi = publish_rssi

    def start(self):
        if self._t and self._t.is_alive():
            return
        self._stop.clear()
        self._t = threading.Thread(target=self._run, daemon=True)  # pragma: no cover
        self._t.start()  # pragma: no cover
        logger.info({"event": "telemetry_start", "interval_s": self.interval_s})

    def stop(self):
        self._stop.set()
        if self._t:
            self._t.join(timeout=2)  # pragma: no cover
        logger.info({"event": "telemetry_stop"})

    def _run(self):
        while not self._stop.is_set():
            try:
                # --- connectivity probe ---
                is_connected = getattr(self.bridge, "is_connected", None)
                online = bool(is_connected()) if callable(is_connected) else True

                # --- presence publish ---
                cb_presence = self._cb_presence
                if cb_presence is None:
                    cb_presence = getattr(self.bridge, "publish_presence", None)
                if callable(cb_presence):
                    try:
                        cb_presence(online)
                    except Exception as e:
                        logger.warning(
                            {
                                "event": "telemetry_presence_cb_error",
                                "error": repr(e),
                            }
                        )

                # --- rssi probe ---
                get_rssi = getattr(self.bridge, "get_rssi", None)
                dbm = None
                if callable(get_rssi):
                    try:
                        dbm = get_rssi()
                    except Exception as e:
                        logger.warning(
                            {
                                "event": "telemetry_rssi_probe_error",
                                "error": repr(e),
                            }
                        )

                # --- rssi publish ---
                cb_rssi = self._cb_rssi
                if cb_rssi is None:
                    cb_rssi = getattr(self.bridge, "publish_rssi", None)
                if callable(cb_rssi):
                    try:
                        if isinstance(dbm, (int, float, str)):
                            try:
                                cb_rssi(int(dbm))
                            except (ValueError, TypeError) as e:
                                logger.warning(
                                    {
                                        "event": "telemetry_invalid_rssi_conversion",
                                        "dbm": repr(dbm),
                                        "error": repr(e),
                                    }
                                )
                        else:
                            logger.warning(
                                {
                                    "event": "telemetry_invalid_rssi",
                                    "dbm": repr(dbm),
                                }
                            )
                    except Exception as e:
                        logger.warning(
                            {
                                "event": "telemetry_rssi_cb_error",
                                "error": repr(e),
                            }
                        )
            except Exception as e:
                logger.warning({"event": "telemetry_error", "error": repr(e)})
            finally:
                sleep_interval = self.sleep_interval
                slept = 0.0
                while slept < self.interval_s and not self._stop.is_set():
                    time.sleep(sleep_interval)
                    slept += sleep_interval

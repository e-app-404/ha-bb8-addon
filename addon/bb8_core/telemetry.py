"""Telemetry helpers: periodic probes and publishing helpers.

This module provides a small background helper that probes a bridge for
connectivity and publishes presence/RSSI via callback hooks or bridge
methods. Edits here are intentionally non-functional and focus on
concise documentation for public APIs.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable

from .logging_setup import logger


class Telemetry:
    """Background telemetry probe and publisher.

    The Telemetry object periodically probes the provided ``bridge`` for
    connectivity and optionally publishes presence and RSSI values using
    supplied callbacks or bridge-provided methods.
    """

    def __init__(
        self,
        bridge,
        interval_s: int = 20,
        publish_presence: Callable[[bool], None] | None = None,
        publish_rssi: Callable[[int], None] | None = None,
    ):
        self.bridge = bridge
        self.interval_s = interval_s
        self._stop = threading.Event()
        self._t = None
        self._cb_presence = publish_presence
        self._cb_rssi = publish_rssi

    def start(self):
        """Start the telemetry background thread if not already running."""

    def stop(self):
        """Stop the telemetry thread and join it (briefly)."""
        if self._t and self._t.is_alive():
            self._stop.clear()
            self._t = threading.Thread(target=self._run, daemon=True)
            self._t.start()
            logger.info({"event": "telemetry_start", "interval_s": self.interval_s})

    def _run(self):
        """Background loop: probe connectivity and publish presence/RSSI."""
        self._stop.set()
        if self._t:
            self._t.join(timeout=2)
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
                            },
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
                            },
                        )

                # --- rssi publish ---
                cb_rssi = self._cb_rssi
                if cb_rssi is None:
                    cb_rssi = getattr(self.bridge, "publish_rssi", None)
                if callable(cb_rssi) and dbm is not None:
                    try:
                        # Use tuple form for isinstance checks
                        if isinstance(dbm, (int, float, str)):
                            cb_rssi(int(dbm))
                        else:
                            logger.warning(
                                {
                                    "event": "telemetry_invalid_rssi",
                                    "dbm": repr(dbm),
                                },
                            )
                    except Exception as e:
                        logger.warning(
                            {
                                "event": "telemetry_rssi_cb_error",
                                "error": repr(e),
                            },
                        )
            except Exception as e:
                logger.warning({"event": "telemetry_error", "error": repr(e)})
            finally:
                time.sleep(self.interval_s)


from __future__ import annotations
import threading
import time
import logging
from .logging_setup import logger
from typing import Optional, Callable

class Telemetry:
    def __init__(
        self,
        bridge,
        interval_s: int = 20,
        publish_presence: Optional[Callable[[bool], None]] = None,
        publish_rssi: Optional[Callable[[int], None]] = None,
    ):
        self.bridge = bridge
        self.interval_s = interval_s
        self._stop = threading.Event()
        self._t = None
        self._cb_presence = publish_presence
        self._cb_rssi = publish_rssi

    def start(self):
        if self._t and self._t.is_alive():
            return
        self._stop.clear()
        self._t = threading.Thread(target=self._run, daemon=True)
        self._t.start()
        logger.info({"event": "telemetry_start", "interval_s": self.interval_s})

    def stop(self):
        self._stop.set()
        if self._t:
            self._t.join(timeout=2)
        logger.info({"event": "telemetry_stop"})

    def _run(self):
        while not self._stop.is_set():
            try:
                # --- connectivity probe ---
                is_connected = getattr(self.bridge, "is_connected", None)
                if callable(is_connected):
                    online = bool(is_connected())
                else:
                    online = True  # or False, depending on your default

                # --- presence publish ---
                cb_presence = self._cb_presence
                if cb_presence is None:
                    cb_presence = getattr(self.bridge, "publish_presence", None)
                if callable(cb_presence):
                    try:
                        cb_presence(online)
                    except Exception as e:
                        logger.warning({"event": "telemetry_presence_cb_error", "error": repr(e)})

                # --- rssi probe ---
                get_rssi = getattr(self.bridge, "get_rssi", None)
                dbm = None
                if callable(get_rssi):
                    try:
                        dbm = get_rssi()
                    except Exception as e:
                        logger.warning({"event": "telemetry_rssi_probe_error", "error": repr(e)})

                # --- rssi publish ---
                cb_rssi = self._cb_rssi
                if cb_rssi is None:
                    cb_rssi = getattr(self.bridge, "publish_rssi", None)
                if callable(cb_rssi) and dbm is not None:
                    try:
                        if isinstance(dbm, (int, float, str)):
                            cb_rssi(int(dbm))
                        else:
                            logger.warning({"event": "telemetry_invalid_rssi", "dbm": repr(dbm)})
                    except Exception as e:
                        logger.warning({"event": "telemetry_rssi_cb_error", "error": repr(e)})
            except Exception as e:
                logger.warning({"event": "telemetry_error", "error": repr(e)})
            finally:
                time.sleep(self.interval_s)


from __future__ import annotations

import contextlib
import json
import os
import queue
import threading
import time
from typing import Any


class EvidenceRecorder:
    """
    Subscribes to command and state topics and records round-trip evidence.
    Constraints:
      - Single publisher (façade) policy remains intact; this only records.
      - Writes JSON lines to reports/ha_mqtt_trace_snapshot.jsonl (≤150 lines).
    """

    def __init__(
        self,
        client,
        topic_prefix: str,
        report_path: str,
        max_lines: int = 150,
        timeout_s: float = 2.0,
    ):
        self.client = client
        self.topic_prefix = topic_prefix.rstrip("/")
        self.report_path = report_path
        self.max_lines = max_lines
        self.timeout_s = timeout_s
        self._cmd_q: queue.Queue[dict[str, Any]] = queue.Queue()
        self._evt_q: queue.Queue[dict[str, Any]] = queue.Queue()
        self._stop = threading.Event()
        self._t: threading.Thread | None = None

    def start(self):
        if self._t and self._t.is_alive():
            return
        self._stop.clear()
        self._install_callbacks()  # pragma: no cover
        self._t = threading.Thread(
            target=self._runner, name="stp4_evidence", daemon=True
        )  # pragma: no cover
        self._t.start()  # pragma: no cover

    def stop(self):
        self._stop.set()
        if self._t:
            self._t.join(timeout=1.0)  # pragma: no cover

    def _install_callbacks(self):
        cmd_topic = f"{self.topic_prefix}/cmd/#"
        state_topic = f"{self.topic_prefix}/state/#"
        self.client.subscribe(cmd_topic, qos=1)  # pragma: no cover
        self.client.subscribe(state_topic, qos=1)  # pragma: no cover

        def on_message(client, userdata, msg):
            now = time.time()
            try:
                payload = msg.payload.decode("utf-8", "ignore")
            except Exception:
                payload = "<binary>"
            evt = {"ts": now, "topic": msg.topic, "payload": payload}
            (self._cmd_q if "/cmd/" in msg.topic else self._evt_q).put(evt)

        old = getattr(self.client, "on_message", None)

        def chained(client, userdata, msg):
            if callable(old):
                with contextlib.suppress(Exception):
                    old(client, userdata, msg)
            on_message(client, userdata, msg)
            on_message(client, userdata, msg)

        self.client.on_message = chained  # pragma: no cover

    def _runner(self):
        lines = 0
        os.makedirs(
            os.path.dirname(self.report_path), exist_ok=True
        )  # pragma: no cover
        with open(self.report_path, "a", encoding="utf-8") as out:  # pragma: no cover
            while not self._stop.is_set() and lines < self.max_lines:
                try:
                    cmd = self._cmd_q.get(timeout=0.5)
                except queue.Empty:
                    continue
                deadline = cmd["ts"] + self.timeout_s
                echo = None
                while time.time() < deadline:
                    try:
                        evt = self._evt_q.get(timeout=deadline - time.time())
                    except queue.Empty:
                        break
                    if evt["topic"].split("/")[-1] == cmd["topic"].split("/")[-1]:
                        echo = evt
                        break
                record = {
                    "phase": "STP4",
                    "cmd": cmd,
                    "echo": echo,
                    "latency_ms": (
                        int((echo["ts"] - cmd["ts"]) * 1000) if echo else None
                    ),
                    "result": "PASS" if echo else "FAIL",
                }
                out.write(
                    json.dumps(record, ensure_ascii=False) + "\n"
                )  # pragma: no cover
                out.flush()  # pragma: no cover
                lines += 1

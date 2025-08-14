from __future__ import annotations
import json, time, threading, queue, os
from typing import Any, Dict, Optional

class EvidenceRecorder:
    """
    Subscribes to command and state topics and records round-trip evidence.
    Constraints:
      - Single publisher (façade) policy remains intact; this only records.
      - Writes JSON lines to reports/ha_mqtt_trace_snapshot.jsonl (≤150 lines).
    """
    def __init__(self, client, topic_prefix: str, report_path: str,
                 max_lines: int = 150, timeout_s: float = 2.0):
        self.client = client
        self.topic_prefix = topic_prefix.rstrip("/")
        self.report_path = report_path
        self.max_lines = max_lines
        self.timeout_s = timeout_s
        self._cmd_q: "queue.Queue[Dict[str, Any]]" = queue.Queue()
        self._evt_q: "queue.Queue[Dict[str, Any]]" = queue.Queue()
        self._stop = threading.Event()
        self._t: Optional[threading.Thread] = None

    def start(self):
        if self._t and self._t.is_alive(): return
        self._stop.clear()
        self._install_callbacks()
        self._t = threading.Thread(target=self._runner, name="stp4_evidence", daemon=True)
        self._t.start()

    def stop(self):
        self._stop.set()
        if self._t: self._t.join(timeout=1.0)

    def _install_callbacks(self):
        cmd_topic = f"{self.topic_prefix}/cmd/#"
        state_topic = f"{self.topic_prefix}/state/#"
        self.client.subscribe(cmd_topic, qos=1)
        self.client.subscribe(state_topic, qos=1)

        def on_message(_c, _u, msg):
            now = time.time()
            try: payload = msg.payload.decode("utf-8", "ignore")
            except Exception: payload = "<binary>"
            evt = {"ts": now, "topic": msg.topic, "payload": payload}
            (self._cmd_q if "/cmd/" in msg.topic else self._evt_q).put(evt)

        old = getattr(self.client, "on_message", None)
        def chained(client, userdata, msg):
            if callable(old):
                try: old(client, userdata, msg)
                except Exception: pass
            on_message(client, userdata, msg)
        self.client.on_message = chained

    def _runner(self):
        lines = 0
        os.makedirs(os.path.dirname(self.report_path), exist_ok=True)
        out = open(self.report_path, "a", encoding="utf-8")
        try:
            while not self._stop.is_set() and lines < self.max_lines:
                try: cmd = self._cmd_q.get(timeout=0.5)
                except queue.Empty: continue
                deadline = cmd["ts"] + self.timeout_s
                echo = None
                while time.time() < deadline:
                    try: evt = self._evt_q.get(timeout=deadline - time.time())
                    except queue.Empty: break
                    if evt["topic"].split("/")[-1] == cmd["topic"].split("/")[-1]:
                        echo = evt; break
                record = {
                    "phase": "STP4",
                    "cmd": cmd,
                    "echo": echo,
                    "latency_ms": int((echo["ts"] - cmd["ts"]) * 1000) if echo else None,
                    "result": "PASS" if echo else "FAIL"
                }
                out.write(json.dumps(record, ensure_ascii=False) + "\n"); out.flush()
                lines += 1
        finally:
            out.close()

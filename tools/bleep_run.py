"""Tiny safe bleep runner.

Safe, minimal runner that uses an in-memory MQTT seam by default.
It publishes a small LED ON/OFF sequence and writes a short report
under reports/ for inspection.
"""

from __future__ import annotations

import datetime
import json
import os
import pathlib
import time
import typing

REPORTS = pathlib.Path("reports") / "bleep_run"
REPORTS.mkdir(parents=True, exist_ok=True)


class FakeMQTT:
    """Very small in-memory MQTT-like seam for tests."""

    def __init__(self) -> None:
        self.published: list[tuple[str, str, bool, int]] = []
        self.subscriptions: dict[str, typing.Any] = {}

    def publish(
        self,
        topic: str,
        payload: str,
        retain: bool = False,
        qos: int = 1,
    ) -> None:
        self.published.append((topic, payload, retain, qos))

    def subscribe(self, topic: str, handler: typing.Any) -> None:
        self.subscriptions[topic] = handler

    def trigger(self, topic: str, payload: str) -> None:
        if topic in self.subscriptions:
            self.subscriptions[topic](payload)


class MinimalController:
    """Echo LED set messages back onto a retained state topic."""

    def __init__(self, base: str) -> None:
        self.base = base

    def attach_mqtt(
        self,
        client: typing.Any,
        qos: int = 1,
        retain: bool = True,
    ) -> None:
        cmd = f"{self.base}/cmd/led/set"
        state = f"{self.base}/state/led"

        def on_led(payload: str) -> None:
            try:
                data = json.loads(payload or "{}")
                r = int(data.get("r", 0))
                g = int(data.get("g", 0))
                b = int(data.get("b", 0))
                client.publish(
                    state,
                    json.dumps({"r": r, "g": g, "b": b}),
                    retain=retain,
                    qos=qos,
                )
            except Exception:
                return

        client.subscribe(cmd, on_led)
        client.publish(f"{self.base}/status", "online", retain=True, qos=qos)


def _write_report(path: pathlib.Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_bleep(dry_run: bool = True) -> int:
    base = os.getenv("MQTT_BASE", "bb8")
    device = os.getenv("DEVICE_ID", "testbb8")

    client = FakeMQTT()
    controller = MinimalController(f"{base}/{device}")
    controller.attach_mqtt(client)

    # Publish LED ON then OFF
    on_payload = json.dumps({"r": 255, "g": 160, "b": 0})
    client.trigger(
        f"{base}/{device}/cmd/led/set",
        on_payload,
    )
    time.sleep(0.05)
    off_payload = json.dumps({"r": 0, "g": 0, "b": 0})
    client.trigger(
        f"{base}/{device}/cmd/led/set",
        off_payload,
    )

    state_topic = f"{base}/{device}/state/led"
    published = getattr(client, "published", [])
    state_pubs = [(t, p, r) for (t, p, r, _q) in published if t == state_topic]
    ok = len(state_pubs) >= 1

    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    out = REPORTS / f"bleep_run_{ts}.log"
    lines = [
        f"bleep_run: dry_run={dry_run}",
        f"base={base}",
        f"device={device}",
    ]
    for t, p, r, _q in published:
        lines.append(
            f"pub: {t} -> {p} (retain={r})",
        )
    lines.append(f"retained_ok={ok}")
    _write_report(out, lines)
    print(f"Wrote report: {out}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(run_bleep())

import asyncio
import sys
from pathlib import Path

# Add repository root to path for test imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import bb8_core.bridge_controller as bc  # type: ignore[import-not-found]


class _FakeLogger:
    def __init__(self):
        self.events = []

    def _capture(self, payload):
        if isinstance(payload, dict):
            event = payload.get("event")
            if event:
                self.events.append(event)

    def info(self, payload, *args, **kwargs):
        self._capture(payload)

    def warning(self, payload, *args, **kwargs):
        self._capture(payload)

    def error(self, payload, *args, **kwargs):
        self._capture(payload)

    def debug(self, payload, *args, **kwargs):
        self._capture(payload)


class _FakeSession:
    def __init__(self):
        self.connect_calls = 0

    def is_connected(self):
        return False

    async def connect(self):
        self.connect_calls += 1

    async def battery(self):
        return 0


class _FakeFacade:
    publish_presence = None

    def mark_post_connect_holdoff(self):
        return None


def _install_loop_exit_sleep(monkeypatch, loops: int):
    counter = {"n": 0}

    async def _fake_sleep(_seconds):
        counter["n"] += 1
        if counter["n"] > loops:
            raise asyncio.CancelledError()

    monkeypatch.setattr(bc.asyncio, "sleep", _fake_sleep)


def test_unhealthy_probe_opens_circuit(monkeypatch):
    fake_logger = _FakeLogger()
    monkeypatch.setattr(bc, "logger", fake_logger)
    monkeypatch.setattr(
        bc,
        "probe_bluez_health",
        lambda **kwargs: asyncio.sleep(0, result={
            "healthy": False,
            "reason": "bluez_inactive",
            "metadata": {"source": "test"},
        }),
    )

    async def _fake_publish(_metrics, _config):
        return None

    monkeypatch.setattr(bc, "_publish_health_metrics", _fake_publish)
    _install_loop_exit_sleep(monkeypatch, loops=1)

    session = _FakeSession()
    asyncio.run(
        bc._start_watchdog(
            _FakeFacade(),
            session,
            {
                "watchdog_interval_s": 0,
                "max_reconnect_attempts": 3,
                "enable_bluez_health_probe": True,
                "bluez_circuit_recheck_s": 30,
            },
        )
    )

    assert session.connect_calls == 0
    assert "bluez_health_failed" in fake_logger.events
    assert "bluez_circuit_open" in fake_logger.events


def test_open_circuit_suppresses_reconnect_until_recheck(monkeypatch):
    fake_logger = _FakeLogger()
    monkeypatch.setattr(bc, "logger", fake_logger)

    probe_calls = {"n": 0}

    async def _probe(**kwargs):
        probe_calls["n"] += 1
        return {
            "healthy": False,
            "reason": "bluez_inactive",
            "metadata": {"source": "test"},
        }

    async def _fake_publish(_metrics, _config):
        return None

    monkeypatch.setattr(bc, "probe_bluez_health", _probe)
    monkeypatch.setattr(bc, "_publish_health_metrics", _fake_publish)
    _install_loop_exit_sleep(monkeypatch, loops=2)

    session = _FakeSession()
    asyncio.run(
        bc._start_watchdog(
            _FakeFacade(),
            session,
            {
                "watchdog_interval_s": 0,
                "max_reconnect_attempts": 3,
                "enable_bluez_health_probe": True,
                "bluez_circuit_recheck_s": 30,
            },
        )
    )

    assert probe_calls["n"] == 1
    assert session.connect_calls == 0
    assert fake_logger.events.count("bluez_circuit_open") >= 2


def test_recheck_closes_circuit_and_reconnect_resumes(monkeypatch):
    fake_logger = _FakeLogger()
    monkeypatch.setattr(bc, "logger", fake_logger)

    responses = [
        {
            "healthy": False,
            "reason": "bluez_inactive",
            "metadata": {"source": "test"},
        },
        {
            "healthy": True,
            "reason": "ok",
            "metadata": {"source": "test"},
        },
    ]

    async def _probe(**kwargs):
        return responses.pop(0)

    async def _fake_publish(_metrics, _config):
        return None

    monotonic_values = iter([0.0, 0.1, 2.0])

    def _fake_monotonic():
        try:
            return next(monotonic_values)
        except StopIteration:
            return 2.0

    monkeypatch.setattr(bc, "probe_bluez_health", _probe)
    monkeypatch.setattr(bc, "_publish_health_metrics", _fake_publish)
    monkeypatch.setattr(bc.time, "monotonic", _fake_monotonic)
    _install_loop_exit_sleep(monkeypatch, loops=2)

    session = _FakeSession()
    asyncio.run(
        bc._start_watchdog(
            _FakeFacade(),
            session,
            {
                "watchdog_interval_s": 0,
                "max_reconnect_attempts": 3,
                "enable_bluez_health_probe": True,
                "bluez_circuit_recheck_s": 1,
            },
        )
    )

    assert session.connect_calls == 1
    assert "bluez_circuit_recheck" in fake_logger.events
    assert "bluez_circuit_closed" in fake_logger.events

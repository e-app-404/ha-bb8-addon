import asyncio
import sys
from pathlib import Path

# Add repository root to path for test imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import bb8_core.bridge_controller as bc  # type: ignore[import-not-found]


class _FakeSession:
    def __init__(self):
        self.connected = True
        self.connect_calls = 0

    def is_connected(self):
        return self.connected

    async def connect(self):
        self.connect_calls += 1
        self.connected = True

    async def battery(self):
        return 0


class _FakeFacade:
    publish_presence = None

    def mark_post_connect_holdoff(self):
        return None


def test_watchdog_publishes_disconnected_after_session_invalidation(monkeypatch):
    published_states = []
    session = _FakeSession()
    sleep_calls = {"count": 0}

    async def _fake_publish(_metrics, _config):
        return None

    def _publish_connection(state, *, config=None):
        published_states.append(state)

    async def _fake_sleep(_seconds):
        sleep_calls["count"] += 1
        if sleep_calls["count"] == 2:
            session.connected = False
        if sleep_calls["count"] > 2:
            raise asyncio.CancelledError()

    monkeypatch.setattr(bc, "_publish_health_metrics", _fake_publish)
    monkeypatch.setattr(bc, "_publish_connection_availability", _publish_connection)
    monkeypatch.setattr(bc.asyncio, "sleep", _fake_sleep)

    asyncio.run(
        bc._start_watchdog(
            _FakeFacade(),
            session,
            {
                "watchdog_interval_s": 0,
                "max_reconnect_attempts": 3,
                "enable_bluez_health_probe": False,
            },
        )
    )

    assert published_states == ["connected", "disconnected", "connected"]
    assert session.connect_calls == 1
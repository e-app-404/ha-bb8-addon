import asyncio
import sys
from pathlib import Path

# Add repository root to path for test imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from bb8_core.host_bluetooth_recovery import (  # type: ignore[import-not-found]
    HostBluetoothRestartRecovery,
)


def test_restart_skipped_when_disabled() -> None:
    events: list[dict] = []
    action = HostBluetoothRestartRecovery(enabled=False, cooldown_s=30, supervisor_token="token")

    result = asyncio.run(
        action.request_restart(
            reason="unit-test",
            emit=events.append,
        )
    )

    assert result["status"] == "skipped_disabled"
    assert result["classification"] == "disabled"
    assert [evt["event"] for evt in events] == [
        "recovery_restart_requested",
        "recovery_restart_skipped_disabled",
    ]


def test_restart_skipped_during_cooldown() -> None:
    action = HostBluetoothRestartRecovery(enabled=True, cooldown_s=20, supervisor_token="token")

    def http_requester(method, url, headers, timeout_s):
        return 200, "{}", ""

    first = asyncio.run(
        action.request_restart(
            reason="first",
            now_fn=lambda: 100.0,
            http_requester=http_requester,
        )
    )
    second = asyncio.run(
        action.request_restart(
            reason="second",
            now_fn=lambda: 105.0,
        )
    )

    assert first["status"] == "succeeded"
    assert first["path"] == "supervisor"
    assert second["status"] == "skipped_cooldown"
    assert second["classification"] == "cooldown_active"
    assert second["remaining_s"] > 0


def test_restart_succeeds_via_supervisor_primary() -> None:
    calls: list[str] = []
    events: list[dict] = []
    action = HostBluetoothRestartRecovery(enabled=True, cooldown_s=30, supervisor_token="token")

    def http_requester(method, url, headers, timeout_s):
        calls.append(url)
        return 200, "{}", ""

    result = asyncio.run(
        action.request_restart(
            reason="unit-test",
            http_requester=http_requester,
            emit=events.append,
        )
    )

    assert result["status"] == "succeeded"
    assert result["path"] == "supervisor"
    assert result["classification"] == "supervisor_success"
    assert calls and calls[0].endswith("/host/service/bluetooth/restart")
    assert [evt["event"] for evt in events] == [
        "recovery_restart_requested",
        "recovery_restart_attempted",
        "recovery_restart_succeeded",
    ]


def test_restart_falls_back_to_dbus_when_supervisor_fails() -> None:
    action = HostBluetoothRestartRecovery(enabled=True, cooldown_s=30, supervisor_token="token")

    def http_requester(method, url, headers, timeout_s):
        if url.endswith("/host/service/bluetooth/restart"):
            return 404, "{}", "HTTP Error 404: Not Found"
        if url.endswith("/host/service/bluetooth/reload"):
            return 503, "{}", "HTTP Error 503: Service Unavailable"
        return 0, "", "unexpected"

    dbus_calls: list[list[str]] = []

    def command_runner(args, timeout_s):
        dbus_calls.append(args)
        return 0, 'o "/org/freedesktop/systemd1/job/123"', ""

    result = asyncio.run(
        action.request_restart(
            reason="unit-test",
            http_requester=http_requester,
            command_runner=command_runner,
        )
    )

    assert result["status"] == "succeeded"
    assert result["path"] == "dbus"
    assert result["classification"] == "dbus_fallback_success"
    assert result["supervisor"]["classification"] == "reachable_error"
    assert result["dbus"]["classification"] == "callable"
    assert dbus_calls
    assert dbus_calls[0][0:2] == ["busctl", "--system"]


def test_restart_fails_when_all_paths_fail() -> None:
    events: list[dict] = []
    action = HostBluetoothRestartRecovery(enabled=True, cooldown_s=30, supervisor_token="token")

    def http_requester(method, url, headers, timeout_s):
        return 403, "{}", "HTTP Error 403: Forbidden"

    def command_runner(args, timeout_s):
        return 1, "", "Access denied"

    result = asyncio.run(
        action.request_restart(
            reason="unit-test",
            http_requester=http_requester,
            command_runner=command_runner,
            emit=events.append,
        )
    )

    assert result["status"] == "failed"
    assert result["classification"] == "all_paths_failed"
    assert result["supervisor"]["classification"] == "unauthorized"
    assert result["dbus"]["classification"] == "unauthorized"
    assert events[-1]["event"] == "recovery_restart_failed"


def test_from_config_parses_enablement_and_cooldown() -> None:
    action = HostBluetoothRestartRecovery.from_config(
        {
            "enable_host_bluetooth_restart_recovery": True,
            "bluetooth_restart_cooldown_s": 45,
        },
        supervisor_token="token",
    )

    assert action.enabled is True
    assert action.cooldown_s == 45

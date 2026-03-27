import asyncio
import sys
from pathlib import Path

import pytest

# Add repository root to path for test imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from bb8_core.recovery_capability_probe import (  # type: ignore[import-not-found]
    probe_host_bluetooth_recovery_capability,
)


def test_probe_reports_callable_systemd_and_available_supervisor(monkeypatch):
    def runner(args, timeout_s):
        if args[:4] == ["busctl", "--system", "get-name-owner", "org.freedesktop.systemd1"]:
            return 0, '"org.freedesktop.systemd1"', ""
        if args[:4] == ["busctl", "--system", "get-property", "org.freedesktop.systemd1"]:
            return 0, 's "255"', ""
        return 1, "", "unexpected"

    def http_getter(url, headers, timeout_s):
        return 200, "{}", ""

    monkeypatch.setenv("SUPERVISOR_TOKEN", "token")

    result = asyncio.run(
        probe_host_bluetooth_recovery_capability(
            source="unit",
            command_runner=runner,
            http_getter=http_getter,
        )
    )

    assert result["system_bus"]["status"] == "reachable"
    assert result["systemd1"]["status"] == "visible"
    assert result["systemd_readonly"]["status"] == "callable"
    assert result["supervisor_api"]["status"] == "available"
    assert result["summary"]["dbus_path_status"] == "reachable_and_callable"
    assert result["summary"]["restart_invokable_inference"] is True


def test_probe_reports_unauthorized_systemd_call(monkeypatch):
    def runner(args, timeout_s):
        if args[:4] == ["busctl", "--system", "get-name-owner", "org.freedesktop.systemd1"]:
            return 0, '"org.freedesktop.systemd1"', ""
        if args[:4] == ["busctl", "--system", "get-property", "org.freedesktop.systemd1"]:
            return 1, "", "Access denied"
        return 1, "", "unexpected"

    monkeypatch.delenv("SUPERVISOR_TOKEN", raising=False)

    result = asyncio.run(
        probe_host_bluetooth_recovery_capability(
            source="unit",
            command_runner=runner,
            http_getter=lambda *_: (0, "", "unreachable"),
        )
    )

    assert result["system_bus"]["status"] == "reachable"
    assert result["systemd_readonly"]["status"] == "unauthorized"
    assert result["summary"]["dbus_path_status"] == "reachable_but_unauthorized"
    assert result["summary"]["restart_invokable_inference"] is False
    assert result["supervisor_api"]["status"] == "not_configured"


def test_probe_reports_unreachable_bus_and_supervisor_unauthorized(monkeypatch):
    def runner(args, timeout_s):
        if args[:4] == ["busctl", "--system", "get-name-owner", "org.freedesktop.systemd1"]:
            return 1, "", "Failed to connect to bus"
        pytest.fail(f"unexpected call: {args}")

    def http_getter(url, headers, timeout_s):
        return 401, "{}", "HTTP Error 401: Unauthorized"

    monkeypatch.setenv("SUPERVISOR_TOKEN", "token")

    result = asyncio.run(
        probe_host_bluetooth_recovery_capability(
            source="unit",
            command_runner=runner,
            http_getter=http_getter,
        )
    )

    assert result["system_bus"]["status"] == "not_reachable"
    assert result["systemd1"]["status"] == "not_visible"
    assert result["systemd_readonly"]["status"] == "skipped"
    assert result["summary"]["dbus_path_status"] == "not_reachable"
    assert result["summary"]["restart_invokable_inference"] is False
    assert result["supervisor_api"]["status"] == "unauthorized"

import sys
from pathlib import Path
import asyncio

import pytest

# Add repository root to path for test imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from bb8_core.bluez_health import probe_bluez_health  # type: ignore[import-not-found]


def _systemctl_probe(args):
    return args[:3] == ["systemctl", "is-active", "bluetooth"]


def _busctl_probe(args):
    return args[:8] == [
        "busctl",
        "--system",
        "call",
        "org.freedesktop.DBus",
        "/org/freedesktop/DBus",
        "org.freedesktop.DBus",
        "GetNameOwner",
        "s",
    ]


def test_probe_bluez_health_healthy():
    calls = []

    def runner(args, timeout_s):
        calls.append((args, timeout_s))
        if _systemctl_probe(args):
            return 0, "active", ""
        if _busctl_probe(args):
            return 0, '"org.bluez"', ""
        return 1, "", "unexpected"

    result = asyncio.run(probe_bluez_health(source="unit", runner=runner))

    assert result["healthy"] is True
    assert result["reason"] == "ok"
    assert result["metadata"]["bluez_active"] is True
    assert result["metadata"]["dbus_owned"] is True
    assert result["metadata"]["source"] == "unit"
    assert len(calls) == 2


def test_probe_bluez_health_healthy_when_systemctl_missing_but_dbus_owned():
    def runner(args, timeout_s):
        if _systemctl_probe(args):
            return 1, "", "[Errno 2] No such file or directory: 'systemctl'"
        if _busctl_probe(args):
            return 0, '"org.bluez"', ""
        return 1, "", "unexpected"

    result = asyncio.run(probe_bluez_health(source="unit", runner=runner))

    assert result["healthy"] is True
    assert result["reason"] == "ok_dbus_only"
    assert result["metadata"]["dbus_owned"] is True
    assert result["metadata"]["bluez_active"] is True
    assert result["metadata"]["service_manager"] == "systemctl_missing"
    assert "service_manager_note" in result["metadata"]
    assert "active_error" not in result["metadata"]


def test_probe_bluez_health_unhealthy_returns_structured_result():
    def runner(args, timeout_s):
        if _systemctl_probe(args):
            return 3, "inactive", ""
        if _busctl_probe(args):
            return 1, "", "name not found"
        return 1, "", "unexpected"

    result = asyncio.run(probe_bluez_health(source="unit", runner=runner))

    assert result["healthy"] is False
    assert result["reason"] == "bluez_inactive_and_unowned"
    assert result["metadata"]["bluez_active"] is False
    assert result["metadata"]["dbus_owned"] is False


def test_probe_bluez_health_unhealthy_when_dbus_unowned_even_if_systemctl_missing():
    def runner(args, timeout_s):
        if _systemctl_probe(args):
            return 1, "", "[Errno 2] No such file or directory: 'systemctl'"
        if _busctl_probe(args):
            return 1, "", "name not found"
        return 1, "", "unexpected"

    result = asyncio.run(probe_bluez_health(source="unit", runner=runner))

    assert result["healthy"] is False
    assert result["reason"] == "bluez_inactive_and_unowned"
    assert result["metadata"]["dbus_owned"] is False
    assert result["metadata"]["bluez_active"] is False
    assert result["metadata"]["service_manager"] == "systemctl_missing"


def test_probe_bluez_health_runner_type_error():
    with pytest.raises(TypeError):
        asyncio.run(probe_bluez_health(source="unit", runner="not-callable"))

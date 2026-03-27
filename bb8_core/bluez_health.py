from __future__ import annotations

import asyncio
import subprocess
import time
from collections.abc import Callable
from typing import Any


def _run_command(args: list[str], timeout_s: float) -> tuple[int, str, str]:
    """Run a local command and return (returncode, stdout, stderr)."""
    try:
        completed = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            check=False,
        )
        return completed.returncode, completed.stdout.strip(), completed.stderr.strip()
    except Exception as exc:  # noqa: BLE001
        return 1, "", str(exc)


async def probe_bluez_health(
    *,
    source: str,
    timeout_s: float = 2.0,
    runner: Callable[[list[str], float], tuple[int, str, str]] | None = None,
) -> dict[str, Any]:
    """Probe BlueZ health using service and DBus ownership checks.

    Returns a structured payload:
    {
      "healthy": bool,
      "reason": str,
      "metadata": {
        "dbus_owned": bool,
        "bluez_active": bool,
        "checked_at": str,
        "source": str,
      }
    }
    """
    if runner is None:
        runner = _run_command
    if not callable(runner):
        raise TypeError("runner must be callable")

    checked_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    active_rc, active_out, active_err = await asyncio.to_thread(
        runner,
        ["systemctl", "is-active", "bluetooth"],
        float(timeout_s),
    )
    bluez_active = active_rc == 0 and active_out.strip() == "active"

    owner_rc, owner_out, owner_err = await asyncio.to_thread(
        runner,
        ["busctl", "--system", "get-name-owner", "org.bluez"],
        float(timeout_s),
    )
    dbus_owned = owner_rc == 0 and bool(owner_out.strip())

    if bluez_active and dbus_owned:
        reason = "ok"
    elif not bluez_active and not dbus_owned:
        reason = "bluez_inactive_and_unowned"
    elif not bluez_active:
        reason = "bluez_inactive"
    else:
        reason = "bluez_unowned"

    metadata: dict[str, Any] = {
        "dbus_owned": dbus_owned,
        "bluez_active": bluez_active,
        "checked_at": checked_at,
        "source": source,
    }

    if active_err:
        metadata["active_error"] = active_err
    if owner_err:
        metadata["owner_error"] = owner_err

    return {
        "healthy": bluez_active and dbus_owned,
        "reason": reason,
        "metadata": metadata,
    }

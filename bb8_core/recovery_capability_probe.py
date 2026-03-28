from __future__ import annotations

import asyncio
import os
import subprocess
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from typing import Any

CommandRunner = Callable[[list[str], float], tuple[int, str, str]]
HttpGetter = Callable[[str, dict[str, str], float], tuple[int, str, str]]


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


def _http_get(url: str, headers: dict[str, str], timeout_s: float) -> tuple[int, str, str]:
    """Issue a GET request and return (status_code, body, error_text)."""
    req = urllib.request.Request(url, method="GET", headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as response:  # noqa: S310
            body = response.read().decode("utf-8", "replace")
            return int(response.status), body, ""
    except urllib.error.HTTPError as exc:
        try:
            body = exc.read().decode("utf-8", "replace")
        except Exception:  # noqa: BLE001
            body = ""
        return int(exc.code), body, str(exc)
    except Exception as exc:  # noqa: BLE001
        return 0, "", str(exc)


def _is_unauthorized(stderr_text: str, stdout_text: str) -> bool:
    message = f"{stderr_text}\n{stdout_text}".lower()
    markers = (
        "access denied",
        "not authorized",
        "permission denied",
        "interactive authentication required",
        "org.freedesktop.dbus.error.accessdenied",
    )
    return any(marker in message for marker in markers)


async def probe_host_bluetooth_recovery_capability(
    *,
    source: str,
    timeout_s: float = 2.0,
    command_runner: CommandRunner | None = None,
    http_getter: HttpGetter | None = None,
) -> dict[str, Any]:
    """Probe host recovery capabilities without mutating host state.

    This probe is intentionally read-only. It does not restart services.
    """
    if command_runner is None:
        command_runner = _run_command
    if http_getter is None:
        http_getter = _http_get
    if not callable(command_runner):
        raise TypeError("command_runner must be callable")
    if not callable(http_getter):
        raise TypeError("http_getter must be callable")

    checked_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    result: dict[str, Any] = {
        "probe": "host_bluetooth_recovery_capability",
        "source": source,
        "checked_at": checked_at,
        "system_bus": {},
        "systemd1": {},
        "systemd_readonly": {},
        "supervisor_api": {},
        "summary": {},
    }

    owner_rc, owner_out, owner_err = await asyncio.to_thread(
        command_runner,
        ["busctl", "--system", "get-name-owner", "org.freedesktop.systemd1"],
        float(timeout_s),
    )

    if owner_rc == 0 and owner_out.strip():
        result["system_bus"] = {"status": "reachable", "error": ""}
        result["systemd1"] = {
            "status": "visible",
            "name_owner": owner_out.strip(),
            "error": owner_err,
        }
    else:
        result["system_bus"] = {"status": "not_reachable", "error": owner_err}
        result["systemd1"] = {
            "status": "not_visible",
            "name_owner": "",
            "error": owner_err,
        }

    if result["systemd1"]["status"] == "visible":
        ro_rc, ro_out, ro_err = await asyncio.to_thread(
            command_runner,
            [
                "busctl",
                "--system",
                "get-property",
                "org.freedesktop.systemd1",
                "/org/freedesktop/systemd1",
                "org.freedesktop.systemd1.Manager",
                "Version",
            ],
            float(timeout_s),
        )
        if ro_rc == 0:
            result["systemd_readonly"] = {
                "status": "callable",
                "error": "",
                "response": ro_out,
            }
        elif _is_unauthorized(ro_err, ro_out):
            result["systemd_readonly"] = {
                "status": "unauthorized",
                "error": ro_err or ro_out,
                "response": "",
            }
        else:
            result["systemd_readonly"] = {
                "status": "failed",
                "error": ro_err or ro_out,
                "response": "",
            }
    else:
        result["systemd_readonly"] = {
            "status": "skipped",
            "error": "systemd1_not_visible",
            "response": "",
        }

    supervisor_token = os.environ.get("SUPERVISOR_TOKEN", "").strip()
    supervisor_url_base = os.environ.get("SUPERVISOR_URL", "http://supervisor").rstrip("/")
    supervisor_info_url = f"{supervisor_url_base}/supervisor/info"

    if not supervisor_token:
        result["supervisor_api"] = {
            "status": "not_configured",
            "url": supervisor_info_url,
            "http_status": 0,
            "error": "SUPERVISOR_TOKEN not set",
        }
    else:
        status_code, _body, http_err = await asyncio.to_thread(
            http_getter,
            supervisor_info_url,
            {"Authorization": f"Bearer {supervisor_token}"},
            float(timeout_s),
        )
        if status_code == 200:
            result["supervisor_api"] = {
                "status": "available",
                "url": supervisor_info_url,
                "http_status": status_code,
                "error": "",
            }
        elif status_code in (401, 403):
            result["supervisor_api"] = {
                "status": "unauthorized",
                "url": supervisor_info_url,
                "http_status": status_code,
                "error": http_err,
            }
        elif status_code > 0:
            result["supervisor_api"] = {
                "status": "reachable_error",
                "url": supervisor_info_url,
                "http_status": status_code,
                "error": http_err,
            }
        else:
            result["supervisor_api"] = {
                "status": "unreachable",
                "url": supervisor_info_url,
                "http_status": 0,
                "error": http_err,
            }

    readonly_status = result["systemd_readonly"]["status"]
    if readonly_status == "callable":
        dbus_path_status = "reachable_and_callable"
        restart_invokable = True
    elif readonly_status == "unauthorized":
        dbus_path_status = "reachable_but_unauthorized"
        restart_invokable = False
    elif result["system_bus"]["status"] == "not_reachable":
        dbus_path_status = "not_reachable"
        restart_invokable = False
    else:
        dbus_path_status = "unknown"
        restart_invokable = False

    supervisor_status = result["supervisor_api"].get("status", "unknown")
    if supervisor_status == "available":
        supervisor_auth_status = "authorized"
        supervisor_recovery_invokable = True
    elif supervisor_status in ("unauthorized", "not_configured"):
        supervisor_auth_status = supervisor_status
        supervisor_recovery_invokable = False
    elif supervisor_status == "unreachable":
        supervisor_auth_status = "unreachable"
        supervisor_recovery_invokable = False
    else:
        supervisor_auth_status = "reachable_error"
        supervisor_recovery_invokable = False

    result["summary"] = {
        "dbus_path_status": dbus_path_status,
        "restart_invokable_inference": restart_invokable,
        "supervisor_auth_status": supervisor_auth_status,
        "supervisor_recovery_invokable_inference": supervisor_recovery_invokable,
        "note": "inference based on read-only capability checks; no restart attempted",
    }

    return result

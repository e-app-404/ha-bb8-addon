from __future__ import annotations

import asyncio
import subprocess
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

HttpRequester = Callable[[str, str, dict[str, str], float], tuple[int, str, str]]
CommandRunner = Callable[[list[str], float], tuple[int, str, str]]
NowFn = Callable[[], float]
EmitFn = Callable[[dict[str, Any]], None]


def _http_request(
    method: str,
    url: str,
    headers: dict[str, str],
    timeout_s: float,
) -> tuple[int, str, str]:
    req = urllib.request.Request(url, method=method, headers=headers)
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


def _run_command(args: list[str], timeout_s: float) -> tuple[int, str, str]:
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


@dataclass
class HostBluetoothRestartRecovery:
    enabled: bool = False
    cooldown_s: int = 300
    supervisor_url_base: str = "http://supervisor"
    supervisor_token: str = ""
    _last_attempt_monotonic: float = field(default=-1.0, init=False, repr=False)

    @classmethod
    def from_config(
        cls,
        config: Mapping[str, Any],
        *,
        supervisor_token: str,
        supervisor_url_base: str = "http://supervisor",
    ) -> "HostBluetoothRestartRecovery":
        enabled = bool(config.get("enable_host_bluetooth_restart_recovery", False))
        cooldown_raw = int(config.get("bluetooth_restart_cooldown_s", 300))
        return cls(
            enabled=enabled,
            cooldown_s=max(1, cooldown_raw),
            supervisor_url_base=supervisor_url_base.rstrip("/"),
            supervisor_token=supervisor_token.strip(),
        )

    async def request_restart(
        self,
        *,
        reason: str,
        timeout_s: float = 5.0,
        http_requester: HttpRequester | None = None,
        command_runner: CommandRunner | None = None,
        now_fn: NowFn | None = None,
        emit: EmitFn | None = None,
    ) -> dict[str, Any]:
        if http_requester is None:
            http_requester = _http_request
        if command_runner is None:
            command_runner = _run_command
        if now_fn is None:
            now_fn = time.monotonic
        if emit is None:
            emit = lambda _event: None

        emit({"event": "recovery_restart_requested", "reason": reason})

        if not self.enabled:
            result = {
                "status": "skipped_disabled",
                "path": "none",
                "reason": reason,
                "classification": "disabled",
            }
            emit({"event": "recovery_restart_skipped_disabled", "reason": reason})
            return result

        now_value = float(now_fn())
        if self._last_attempt_monotonic >= 0:
            elapsed = now_value - self._last_attempt_monotonic
            if elapsed < float(self.cooldown_s):
                remaining_s = max(0.0, float(self.cooldown_s) - elapsed)
                result = {
                    "status": "skipped_cooldown",
                    "path": "none",
                    "reason": reason,
                    "classification": "cooldown_active",
                    "remaining_s": remaining_s,
                }
                emit(
                    {
                        "event": "recovery_restart_skipped_cooldown",
                        "reason": reason,
                        "remaining_s": remaining_s,
                    }
                )
                return result

        self._last_attempt_monotonic = now_value

        supervisor_result = await self._attempt_supervisor_restart(
            timeout_s=timeout_s,
            http_requester=http_requester,
            emit=emit,
        )
        if supervisor_result["status"] == "succeeded":
            emit(
                {
                    "event": "recovery_restart_succeeded",
                    "path": "supervisor",
                    "reason": reason,
                }
            )
            return {
                "status": "succeeded",
                "path": "supervisor",
                "reason": reason,
                "classification": "supervisor_success",
                "supervisor": supervisor_result,
            }

        dbus_result = await self._attempt_dbus_restart(
            timeout_s=timeout_s,
            command_runner=command_runner,
            emit=emit,
        )
        if dbus_result["status"] == "succeeded":
            emit(
                {
                    "event": "recovery_restart_succeeded",
                    "path": "dbus",
                    "reason": reason,
                }
            )
            return {
                "status": "succeeded",
                "path": "dbus",
                "reason": reason,
                "classification": "dbus_fallback_success",
                "supervisor": supervisor_result,
                "dbus": dbus_result,
            }

        emit(
            {
                "event": "recovery_restart_failed",
                "reason": reason,
                "supervisor_classification": supervisor_result.get("classification"),
                "dbus_classification": dbus_result.get("classification"),
            }
        )
        return {
            "status": "failed",
            "path": "none",
            "reason": reason,
            "classification": "all_paths_failed",
            "supervisor": supervisor_result,
            "dbus": dbus_result,
        }

    async def _attempt_supervisor_restart(
        self,
        *,
        timeout_s: float,
        http_requester: HttpRequester,
        emit: EmitFn,
    ) -> dict[str, Any]:
        emit({"event": "recovery_restart_attempted", "path": "supervisor"})

        if not self.supervisor_token:
            return {
                "status": "failed",
                "classification": "not_configured",
                "http_status": 0,
                "error": "SUPERVISOR_TOKEN not set",
            }

        headers = {"Authorization": f"Bearer {self.supervisor_token}"}
        services_url = f"{self.supervisor_url_base}/host/services"
        status_code, _body, err = await asyncio.to_thread(
            http_requester,
            "GET",
            services_url,
            headers,
            float(timeout_s),
        )
        if status_code == 200:
            return {
                "status": "failed",
                "classification": "control_path_unavailable",
                "http_status": status_code,
                "endpoint": services_url,
                "error": "host service control endpoint not exposed on this runtime",
            }
        if status_code in (401, 403):
            return {
                "status": "failed",
                "classification": "unauthorized",
                "http_status": status_code,
                "endpoint": services_url,
                "error": err,
            }
        if status_code == 0:
            return {
                "status": "failed",
                "classification": "unreachable",
                "http_status": 0,
                "endpoint": services_url,
                "error": err,
            }
        return {
            "status": "failed",
            "classification": "reachable_error",
            "http_status": int(status_code),
            "endpoint": services_url,
            "error": err,
        }

    async def _attempt_dbus_restart(
        self,
        *,
        timeout_s: float,
        command_runner: CommandRunner,
        emit: EmitFn,
    ) -> dict[str, Any]:
        emit({"event": "recovery_restart_attempted", "path": "dbus"})

        rc, out, err = await asyncio.to_thread(
            command_runner,
            [
                "busctl",
                "--system",
                "call",
                "org.freedesktop.systemd1",
                "/org/freedesktop/systemd1",
                "org.freedesktop.systemd1.Manager",
                "RestartUnit",
                "ss",
                "bluetooth.service",
                "replace",
            ],
            float(timeout_s),
        )
        if rc == 0:
            return {
                "status": "succeeded",
                "classification": "callable",
                "stdout": out,
                "stderr": err,
            }

        message = f"{err}\n{out}".lower()
        if "no such file or directory" in message and "busctl" in message:
            classification = "command_missing"
        elif "access denied" in message or "not authorized" in message:
            classification = "unauthorized"
        else:
            classification = "failed"
        return {
            "status": "failed",
            "classification": classification,
            "stdout": out,
            "stderr": err,
            "returncode": rc,
        }

from __future__ import annotations

import warnings

warnings.filterwarnings(
    "ignore", "Callback API version 1 is deprecated", DeprecationWarning, "paho"
)

import asyncio
import logging
import threading
from collections.abc import Coroutine
from concurrent.futures import Future
from typing import Any

log = logging.getLogger(__name__)
_loop: asyncio.AbstractEventLoop | None = None
_loop_thread: threading.Thread | None = None
_runner_future: Future | None = None
_started: bool = False
_alive_evt = threading.Event()


class BLEConnectionError(Exception):
    """Raised for BLE connection related errors (back-compat shim)."""


def set_loop(loop: asyncio.AbstractEventLoop) -> None:
    """Inject the dedicated BLE loop (created in a separate thread)."""
    global _loop, _loop_thread
    _loop = loop
    log.info("ble_loop_set loop_id=%s", id(loop))


def start_loop_thread() -> None:
    """Start BLE event loop in a dedicated thread if not already running."""
    global _loop, _loop_thread
    if _loop_thread and _loop_thread.is_alive():
        return

    def _run():
        loop = asyncio.new_event_loop()
        set_loop(loop)
        asyncio.set_event_loop(loop)
        log.info("ble_loop_thread_started name=BLELoopThread")
        _alive_evt.set()
        loop.run_forever()

    _loop_thread = threading.Thread(target=_run, name="BLELoopThread", daemon=True)
    _loop_thread.start()
    log.info("ble_loop_thread_spawned")
    # Wait briefly for loop to come up (avoids race in tests)
    _alive_evt.wait(timeout=1.0)


async def _run() -> None:
    """
    BLE worker main coroutine.
    Must only be scheduled on the dedicated loop.
    """
    # gentler exponential-ish backoff with ceiling
    backoff = [0.1, 0.2, 0.5, 1.0, 2.0, 4.0, 8.0, 16.0]
    i = 0
    from .telemetry import ble_connect_attempt

    try:
        while True:
            # ... BLE connect/IO logic ...
            delay = backoff[min(i, len(backoff) - 1)]
            log.info("ble_connect_attempt try=%s backoff=%s", i + 1, delay)
            # Telemetry hook (non-fatal)
            try:
                ble_connect_attempt(globals().get("mqtt_client"), i + 1, delay)
            except Exception:
                pass
            await asyncio.sleep(delay)
            i = min(i + 1, len(backoff) - 1)
    except asyncio.CancelledError:
        log.info("ble_worker_cancelled")
        raise


async def _cancel_and_drain() -> None:
    """
    Run inside BLE loop:
      - cancel all tasks except self
      - wait for their completion without leaking 'unawaited coroutine' warnings
    """
    this = asyncio.current_task()
    tasks = [t for t in asyncio.all_tasks() if t is not this]
    for t in tasks:
        t.cancel()
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)
    # yield once to flush any pending callbacks
    await asyncio.sleep(0)


def start() -> None:
    """Idempotently start the BLE worker on the dedicated loop."""
    global _runner_future, _started
    if _started:
        return
    start_loop_thread()
    if _loop is None:
        raise RuntimeError("BLE loop not set; call set_loop() before start()")
    _runner_future = asyncio.run_coroutine_threadsafe(_run(), _loop)
    _started = True
    log.info("ble_link_runner_started")


def join(timeout: float = 3.0) -> None:
    """Join BLE loop thread if running (idempotent)."""
    global _loop_thread
    if _loop_thread and _loop_thread.is_alive():
        _loop_thread.join(timeout=timeout)


def stop(timeout: float = 3.0) -> None:
    """
    Gracefully stop BLE worker and loop with full async drain,
    then join thread.
    """
    global _runner_future, _started
    if not _started or _runner_future is None:
        return
    fut = _runner_future
    _runner_future = None
    _started = False
    try:
        # 1) cancel the runner task
        fut.cancel()
        # 2) drain all tasks within the BLE loop
        if _loop is not None:
            asyncio.run_coroutine_threadsafe(_cancel_and_drain(), _loop).result(
                timeout=timeout
            )
            # 3) stop the loop and join the thread
            _loop.call_soon_threadsafe(_loop.stop)
        join(timeout=timeout)
    except Exception as e:
        log.warning("ble_link_stop_exception %s", e)


def run_coro(coro: Coroutine[Any, Any, Any]) -> Future:
    """Schedule a coroutine on the dedicated BLE loop."""
    if _loop is None:
        raise RuntimeError("BLE loop not set; call set_loop() first")
    return asyncio.run_coroutine_threadsafe(coro, _loop)


# ---------------------------------------------------------------------------
# Compatibility facade for callers importing `BLELink`
# ---------------------------------------------------------------------------
class BLELink:
    """Compatibility facade providing a minimal BLE link surface used by tests.

    This class is intentionally simple — it does not implement full BLE logic.
    It stores a reference to a gateway object (the tests supply a MagicMock)
    and exposes a few convenience methods/properties used by the tests.
    """

    def __init__(self, device_address: str | None = None, gateway: Any | None = None):
        # Public attributes used by tests
        self.device_address = device_address
        self.gateway = gateway
        # The connected client (None when not connected). Tests may set this
        # directly to a MagicMock to emulate an active connection.
        self.client: Any | None = None

    @property
    def is_connected(self) -> bool:
        """Return True when a client object exists and reports being connected."""
        if self.client is None:
            return False
        return bool(getattr(self.client, "is_connected", False))

    def start(self) -> None:
        """Start the shared BLE runner (idempotent)."""
        start()

    def stop(self, timeout: float = 2.5) -> None:
        """Stop the shared BLE runner cleanly."""
        stop(timeout=timeout)

    def submit(self, coro: Coroutine[Any, Any, Any]) -> Future:
        """Schedule a coroutine onto the dedicated BLE loop."""
        return run_coro(coro)

    # Lightweight connection helpers used by tests
    def connect(self) -> Any:
        """Attempt to connect using the configured gateway.

        The real project uses richer semantics; tests only expect exceptions to
        propagate from the gateway when connection fails.
        """
        if self.gateway is None:
            raise BLEConnectionError("No gateway configured")
        # Delegate to the gateway; tests mock gateway.connect to raise or return
        result = self.gateway.connect(self.device_address)
        # Save returned client when gateway.connect returns one
        if result is not None:
            self.client = result
        return result

    def disconnect(self) -> None:
        """Disconnect the active client if present; otherwise no-op."""
        if self.client is None:
            return
        try:
            # Prefer client-level disconnect if available
            if hasattr(self.client, "disconnect"):
                self.client.disconnect()
            # Otherwise, allow gateway to handle it
            elif self.gateway and hasattr(self.gateway, "disconnect"):
                self.gateway.disconnect(self.client)
        finally:
            self.client = None

    def write_characteristic(self, uuid: str, data: bytes) -> None:
        """Write data to a characteristic on the connected client.

        When no client is connected a BLEConnectionError is raised to match
        existing callers/tests.
        """
        if self.client is None:
            raise BLEConnectionError("Not connected to device")
        # Delegate to client write if present
        if hasattr(self.client, "write_characteristic"):
            return self.client.write_characteristic(uuid, data)
        # Fallback: attempt attribute access which may raise AttributeError
        raise AttributeError("client does not support write_characteristic")


def create_ble_link(device_address: str, gateway: Any | None = None) -> BLELink:
    """Factory helper to create a BLELink instance (convenience wrapper).

    Tests import and call this factory; keeping it small avoids touching the
    larger BLE runner implementation.
    """
    return BLELink(device_address, gateway)


__all__ = [
    "BLEConnectionError",
    "set_loop",
    "start",
    "stop",
    "run_coro",
    "BLELink",
    "create_ble_link",
]

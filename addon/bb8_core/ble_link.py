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


async def _cancel_and_drain() -> int:
    """
    Cancel and await completion of all pending tasks on the BLE loop.
    Must be executed *inside* the BLE loop.
    Returns the number of tasks cancelled.
    """
    print("[BLELink] _cancel_and_drain ENTRY")
    current = asyncio.current_task()
    pending: list[asyncio.Task[Any]] = [
        t for t in asyncio.all_tasks() if t is not current and not t.done()
    ]
    print(f"[BLELink] Pending tasks before cancel: {[str(t) for t in pending]}")
    log.info(f"[BLELink] Pending tasks before cancel: {[str(t) for t in pending]}")
    for t in pending:
        t.cancel()
    print(f"[BLELink] Pending tasks after cancel: {[str(t) for t in pending]}")
    log.info(f"[BLELink] Pending tasks after cancel: {[str(t) for t in pending]}")
    cancelled_count = len(pending)
    if pending:
        print(f"[BLELink] Awaiting {cancelled_count} tasks...")
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*pending, return_exceptions=True), timeout=5.0
            )
            print(f"[BLELink] Gathered results: {results}")
            excs = [r for r in results if isinstance(r, Exception)]
            if excs:
                log.debug(
                    "BLE cleanup gathered %d exception(s): %s",
                    len(excs),
                    ", ".join(type(e).__name__ for e in excs),
                )
        except TimeoutError:
            print("[BLELink] Timeout while awaiting cancelled tasks.")
            log.warning("BLE cleanup timed out while awaiting cancelled tasks.")
    else:
        print("[BLELink] No pending tasks to cancel; immediate completion.")
        log.info("BLE cleanup: no pending tasks; immediate completion.")
        # Small sleep to ensure coroutine yields control
        await asyncio.sleep(0.01)
    print(f"[BLELink] _cancel_and_drain END, cancelled {cancelled_count} tasks.")
    log.info(f"[BLELink] _cancel_and_drain END, cancelled {cancelled_count} tasks.")
    return cancelled_count


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


def join(timeout: float = 3.0) -> None:
    """Join BLE loop thread if running (idempotent)."""
    global _loop_thread
    if _loop_thread and _loop_thread.is_alive():
        _loop_thread.join(timeout=timeout)


def stop(timeout: float = 3.0) -> None:
    """Gracefully stop BLE worker and loop with full async drain, then join thread."""
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
    """
    Minimal facade to satisfy callers/tests that expect a BLELink class.
    Internally delegates to the module-level runner functions above.
    """

    def __init__(self, mac: str | None = None, adapter: str | None = None):
        self.mac = mac
        self.adapter = adapter

    def start(self) -> None:
        """Start the shared BLE runner (idempotent)."""
        start()

    def stop(self, timeout: float = 2.5) -> None:
        """Stop the shared BLE runner cleanly."""
        stop(timeout=timeout)

    def submit(self, coro: Coroutine[Any, Any, Any]) -> Future:
        """
        Schedule a coroutine onto the dedicated BLE loop.
        Example: link.submit(device.connect())
        """
        return run_coro(coro)

    # Optional convenience shims if legacy code calls these:
    def set_loop(self, loop: asyncio.AbstractEventLoop) -> None:  # noqa: D401
        """Delegate to module-level set_loop()."""
        set_loop(loop)


__all__ = [
    "set_loop",
    "start",
    "stop",
    "run_coro",
    "BLELink",
]

from __future__ import annotations


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
        loop.run_forever()
    _loop_thread = threading.Thread(target=_run, name="BLELoopThread", daemon=True)
    _loop_thread.start()
    log.info("ble_loop_thread_spawned")


async def _run() -> None:
    """
    BLE worker main coroutine.
    Must only be scheduled on the dedicated loop.
    """
    # gentler exponential-ish backoff with ceiling
    backoff = [0.1, 0.2, 0.5, 1.0, 2.0, 4.0, 8.0, 16.0]
    i = 0
    try:
        while True:
            # ... BLE connect/IO logic ...
            delay = backoff[min(i, len(backoff) - 1)]
            log.info("ble_connect_attempt try=%s backoff=%s", i + 1, delay)
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
    current = asyncio.current_task()
    # Snapshot all tasks bound to this loop
    pending: list[asyncio.Task[Any]] = [
        t for t in asyncio.all_tasks() if t is not current and not t.done()
    ]
    for t in pending:
        t.cancel()
    if pending:
        results = await asyncio.gather(*pending, return_exceptions=True)
        excs = [r for r in results if isinstance(r, Exception)]
        if excs:
            log.debug(
                "BLE cleanup gathered %d exception(s): %s",
                len(excs),
                ", ".join(type(e).__name__ for e in excs),
            )
    return len(pending)


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


def stop(timeout: float = 2.5) -> None:
    """Cancel the BLE worker and wait for clean shutdown."""
    global _runner_future, _started
    fut = _runner_future
    _runner_future = None
    _started = False
    if fut and not fut.done():
        fut.cancel()
        try:
            fut.result(timeout=timeout)
        except asyncio.CancelledError:
            pass
        except Exception as exc:  # noqa: BLE001
            log.warning("BLE runner stop wait raised: %s", exc)
    # New: drain any other pending tasks still attached to the BLE loop.
    if _loop is not None:
        try:
            drained = asyncio.run_coroutine_threadsafe(
                _cancel_and_drain(), _loop
            ).result(timeout=timeout)
            log.info("BLE cleanup: cancelled %d pending task(s).", drained)
        except TimeoutError:
            log.warning("BLE cleanup timed out after %.2fs.", timeout)
        except Exception as exc:  # noqa: BLE001
            log.warning("BLE cleanup wait raised: %s", exc)


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

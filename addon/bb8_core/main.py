"""Main entrypoint for the bb8_core add-on.

Starts the bridge controller and manages a simple heartbeat/log flush on exit.
"""

# DIAG-BEGIN IMPORTS
import atexit
import contextlib
import os
import signal
import sys
import tempfile
import threading
import time
from pathlib import Path

from addon.bb8_core.logging_setup import logger

# DIAG-END IMPORTS

# DIAG-BEGIN STARTUP-AND-FLUSH


# --- Robust health heartbeat (atomic writes + fsync) ---
def _env_truthy(val: str) -> bool:
    return str(val).strip().lower() in {"1", "true", "yes", "on"}


def _write_atomic(path: str, content: str) -> None:
    p = Path(path)
    tmp = p.with_suffix(p.suffix + ".tmp") if p.suffix else Path(str(p) + ".tmp")
    try:
        with tmp.open("w") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        tmp.replace(p)
    except OSError as e:
        msg = "atomic write failed"
        raise OSError(msg) from e


def _start_heartbeat(path: str, interval: int) -> None:
    interval = max(interval, 2)  # lower bound

    def _hb() -> None:
        # write immediately, then tick
        try:
            _write_atomic(path, f"{time.time()}\n")
        except OSError as e:
            logger.debug("heartbeat initial write failed: %s", e)
        while True:
            try:
                _write_atomic(path, f"{time.time()}\n")
            except OSError as e:
                logger.debug("heartbeat write failed: %s", e)
            time.sleep(interval)

    t = threading.Thread(target=_hb, daemon=True)
    t.start()


ENABLE_HEALTH_CHECKS = _env_truthy(os.environ.get("ENABLE_HEALTH_CHECKS", "0"))
HB_INTERVAL = int(os.environ.get("HEARTBEAT_INTERVAL_SEC", "5"))
HB_PATH_MAIN = str(Path(tempfile.gettempdir()) / "bb8_heartbeat_main")
if ENABLE_HEALTH_CHECKS:
    logger.info(
        "main.py health check enabled: %s interval=%ss",
        HB_PATH_MAIN,
        HB_INTERVAL,
    )
    try:
        _start_heartbeat(HB_PATH_MAIN, HB_INTERVAL)
    except OSError as e:
        logger.warning("Failed to start heartbeat: %s", e)


@atexit.register
def _hb_exit() -> None:
    with contextlib.suppress(OSError):
        _write_atomic(HB_PATH_MAIN, f"{time.time()}\n")


logger.info("bb8_core.main started (PID=%s)", os.getpid())


def _flush_logs() -> None:
    logger.info("main.py atexit: flushing logs before exit")
    for h in getattr(logger, "handlers", []):
        if hasattr(h, "flush"):
            with contextlib.suppress(OSError):
                h.flush()


atexit.register(_flush_logs)
# DIAG-END STARTUP-AND-FLUSH


def main() -> None:
    """Start the bb8_core bridge controller and wait for termination signals."""
    logger.info("bb8_core.main started")
    try:
        from addon.bb8_core.bridge_controller import start_bridge_controller

        # Start the bridge controller and ignore any return value (unused)
        start_bridge_controller()
        logger.info("bridge_controller started; entering run loop")
        # Block main thread until SIGTERM/SIGINT
        stop_evt = False

        def _on_signal(signum: int, _frame: object) -> None:
            logger.info("signal_received signum=%s", signum)
            nonlocal stop_evt
            stop_evt = True

        signal.signal(signal.SIGTERM, _on_signal)
        signal.signal(signal.SIGINT, _on_signal)
        while not stop_evt:
            time.sleep(1)
        logger.info("main exiting after signal")
    except Exception:
        logger.exception("fatal error in main")
        _flush_logs()
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
        logger.info("main.py exited normally")
    except Exception:
        logger.exception("main.py top-level exception")
        _flush_logs()
        sys.exit(1)

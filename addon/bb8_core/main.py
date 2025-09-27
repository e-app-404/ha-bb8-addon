# DIAG-BEGIN IMPORTS
import atexit
import os
import sys
import threading
import time

from bb8_core.logging_setup import logger

# DIAG-END IMPORTS

# DIAG-BEGIN STARTUP-AND-FLUSH


# --- Robust health heartbeat (atomic writes + fsync) ---
def _env_truthy(val: str) -> bool:
    return str(val).strip().lower() in {"1", "true", "yes", "on"}


def _write_atomic(path: str, content: str) -> None:
    tmp = f"{path}.tmp"
    with open(tmp, "w") as f:
        f.write(content)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def _start_heartbeat(path: str, interval: int) -> None:
    interval = 2 if interval < 2 else interval  # lower bound

    def _hb():
        # write immediately, then tick
        try:
            _write_atomic(path, f"{time.time()}\n")
        except Exception as e:
            logger.debug("heartbeat initial write failed: %s", e)
        while True:
            try:
                _write_atomic(path, f"{time.time()}\n")
            except Exception as e:
                logger.debug("heartbeat write failed: %s", e)
            time.sleep(interval)

    t = threading.Thread(target=_hb, daemon=True)
    t.start()


ENABLE_HEALTH_CHECKS = _env_truthy(os.environ.get("ENABLE_HEALTH_CHECKS", "0"))
HB_INTERVAL = int(os.environ.get("HEARTBEAT_INTERVAL_SEC", "5"))
HB_PATH_MAIN = "/tmp/bb8_heartbeat_main"
if ENABLE_HEALTH_CHECKS:
    logger.info(
        "main.py health check enabled: %s interval=%ss", HB_PATH_MAIN, HB_INTERVAL
    )
    _start_heartbeat(HB_PATH_MAIN, HB_INTERVAL)


@atexit.register
def _hb_exit():
    try:
        _write_atomic(HB_PATH_MAIN, f"{time.time()}\n")
    except Exception:
        pass


logger.info(f"bb8_core.main started (PID={os.getpid()})")


def _flush_logs():
    logger.info("main.py atexit: flushing logs before exit")
    for h in getattr(logger, "handlers", []):
        if hasattr(h, "flush"):
            try:
                h.flush()
            except Exception:
                pass


atexit.register(_flush_logs)
# DIAG-END STARTUP-AND-FLUSH


def main():
    logger.info("bb8_core.main started")
    try:
        from bb8_core.bridge_controller import start_bridge_controller

        facade = start_bridge_controller()
        logger.info("bridge_controller started; entering run loop")
        # Block main thread until SIGTERM/SIGINT
        import signal

        stop_evt = False

        def _on_signal(signum, frame):
            logger.info(f"signal_received signum={signum}")
            nonlocal stop_evt
            stop_evt = True

        signal.signal(signal.SIGTERM, _on_signal)
        signal.signal(signal.SIGINT, _on_signal)
        while not stop_evt:
            time.sleep(1)
        logger.info("main exiting after signal")
    except Exception as e:
        logger.exception(f"fatal error in main: {e}")
        _flush_logs()
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
        logger.info("main.py exited normally")
    except Exception as e:
        logger.exception(f"main.py top-level exception: {e}")
        _flush_logs()
        sys.exit(1)

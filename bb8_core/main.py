# DIAG-BEGIN IMPORTS
import atexit
import contextlib
import logging
import os
import signal
import sys
import threading
import time

logger = logging.getLogger(__name__)

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
        "main.py health check enabled: %s interval=%ss",
        HB_PATH_MAIN,
        HB_INTERVAL,
    )
    _start_heartbeat(HB_PATH_MAIN, HB_INTERVAL)


@atexit.register
def _hb_exit():
    with contextlib.suppress(Exception):
        _write_atomic(HB_PATH_MAIN, f"{time.time()}\n")


logger.info(f"bb8_core.main started (PID={os.getpid()})")


def _flush_logs():
    logger.info("main.py atexit: flushing logs before exit")
    for h in getattr(logger, "handlers", []):
        if hasattr(h, "flush"):
            with contextlib.suppress(Exception):
                h.flush()


atexit.register(_flush_logs)
# DIAG-END STARTUP-AND-FLUSH


def main() -> None:
    print("DEBUG: main() function starting", flush=True)
    logger.info("main() starting minimal loop")
    
    try:        
        stop_evt = False

        def _on_signal(signum, frame):
            nonlocal stop_evt
            print(f"DEBUG: signal {signum} received", flush=True)
            logger.info(f"Signal {signum} received, stopping")
            stop_evt = True

        signal.signal(signal.SIGTERM, _on_signal)
        signal.signal(signal.SIGINT, _on_signal)
        print("DEBUG: entering signal loop", flush=True)
        logger.info("Entering main loop")
        
        counter = 0
        while not stop_evt:
            time.sleep(5)
            counter += 1 
            if counter % 6 == 0:  # Every 30 seconds
                logger.info(f"Main process alive, counter={counter}")
                print(f"DEBUG: main alive counter={counter}", flush=True)
                
        print("DEBUG: main exiting after signal", flush=True)
        logger.info("Main exiting after signal")
    except Exception as e:
        print(f"DEBUG: fatal error in main: {e}", flush=True)
        logger.exception(f"Fatal error in main: {e}")
        sys.exit(1)


print(f"DEBUG: __name__ = {__name__}", flush=True)
print(f"DEBUG: __file__ = {__file__}", flush=True)

if __name__ == "__main__":
    print("DEBUG: entering __main__ block", flush=True)
    try:
        main()
        print("DEBUG: main() completed normally", flush=True)
        logger.info("main.py exited normally")
    except Exception as e:
        print(f"DEBUG: top-level exception: {e}", flush=True)
        logger.exception(f"main.py top-level exception: {e}")
        _flush_logs()
        sys.exit(1)
else:
    print(f"DEBUG: __name__ is not __main__, it's {__name__}", flush=True)

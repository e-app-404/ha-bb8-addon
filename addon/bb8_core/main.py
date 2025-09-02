# DIAG-BEGIN IMPORTS
import os
import sys
import time
import atexit
import threading
from bb8_core.logging_setup import logger
# DIAG-END IMPORTS

# DIAG-BEGIN STARTUP-AND-FLUSH
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

# DIAG-BEGIN HEALTH-MAIN
ENABLE_HEALTH_CHECKS = bool(int(os.environ.get("ENABLE_HEALTH_CHECKS", "0")))
def _heartbeat_main():
    while True:
        try:
            with open("/tmp/bb8_heartbeat_main", "w") as f:
                f.write(f"{time.time()}\n")
        except Exception:
            pass
        time.sleep(5)
if ENABLE_HEALTH_CHECKS:
    logger.info("main.py health check enabled: /tmp/bb8_heartbeat_main")
    threading.Thread(target=_heartbeat_main, daemon=True).start()
# DIAG-END HEALTH-MAIN

if __name__ == "__main__":
    try:
        main()
        logger.info("main.py exited normally")
    except Exception as e:
        logger.exception(f"main.py top-level exception: {e}")
        _flush_logs()
        sys.exit(1)


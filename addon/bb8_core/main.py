
import logging
import os
import sys
import time


import sys
import time
from bb8_core.logging_setup import logger

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
        sys.exit(1)


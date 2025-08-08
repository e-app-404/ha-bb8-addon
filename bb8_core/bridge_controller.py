# Bridge Controller: Unified orchestration for Home Assistant add-on
# Finalized for coordinated BLE/MQTT runtime (2025-08-04)

import logging
from logging.handlers import RotatingFileHandler
import os
import sys
from typing import Optional
from bb8_core.ble_bridge import BLEBridge
from bb8_core import mqtt_dispatcher

# --- Log paths ---
LOGFILE = "/config/hestia/diagnostics/logs/ha_bb8_addon.log"
LOG_MAX_BYTES = 2 * 1024 * 1024    # 2 MB per file
LOG_BACKUP_COUNT = 3               # keep last 3 logs

# --- Logging config ---
os.makedirs("/config/hestia/diagnostics/logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s:%(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),  # For Home Assistant UI log tab
        RotatingFileHandler(LOGFILE, maxBytes=LOG_MAX_BYTES, backupCount=LOG_BACKUP_COUNT)
    ],
    force=True
)
logger = logging.getLogger("bb8_addon")
logger.info("BB-8 add-on logging initialized (dual output + rotation)")

# Redirect all print() output to logger
class PrintToLogger:
    def write(self, msg):
        msg = msg.rstrip()
        if msg:
            logger.info(msg)
    def flush(self): pass

sys.stdout = PrintToLogger()
sys.stderr = PrintToLogger()

def start_bridge_controller(
    mqtt_host: str,
    mqtt_port: int,
    mqtt_topic: str,
    mqtt_user: Optional[str] = None,
    mqtt_password: Optional[str] = None,
    status_topic: Optional[str] = None,
) -> None:
    """Starts BLE bridge and MQTT dispatcher in coordinated runtime"""
    try:
        logger.info(f"Initializing BLEBridge")
        bridge = BLEBridge()
        logger.debug(f"BLEBridge instance created: {bridge}")
    except Exception as e:
        logger.error(f"Failed to initialize BLEBridge: {e}", exc_info=True)
        raise
    try:
        logger.info("Starting MQTT dispatcher...")
        logger.debug(f"Calling start_mqtt_dispatcher with host={mqtt_host}, port={mqtt_port}, topic={mqtt_topic}, user={mqtt_user}, status_topic={status_topic}")
        mqtt_dispatcher.start_mqtt_dispatcher(
            mqtt_host=mqtt_host,
            mqtt_port=mqtt_port,
            mqtt_topic=mqtt_topic,
            mqtt_user=mqtt_user,
            mqtt_password=mqtt_password,
            status_topic=status_topic,
            # Optionally pass bridge if dispatcher supports injection
        )
        logger.debug("MQTT dispatcher started successfully.")
    except Exception as e:
        logger.error(f"MQTT dispatcher failed: {e}", exc_info=True)
        try:
            bridge.shutdown()
            logger.debug("BLEBridge shutdown completed after dispatcher failure.")
        except Exception as de:
            logger.error(f"Error during BLEBridge shutdown: {de}", exc_info=True)
        raise

if __name__ == "__main__":
    # Entrypoint for run.sh
    mqtt_host = os.getenv("MQTT_HOST", "localhost")
    mqtt_port = int(os.getenv("MQTT_PORT", "1883"))
    mqtt_topic = os.getenv("MQTT_TOPIC", "bb8/command")
    mqtt_user = os.getenv("MQTT_USER")
    mqtt_password = os.getenv("MQTT_PASSWORD")
    status_topic = os.getenv("STATUS_TOPIC", "bb8/status")
    start_bridge_controller(
        mqtt_host=mqtt_host,
        mqtt_port=mqtt_port,
        mqtt_topic=mqtt_topic,
        mqtt_user=mqtt_user,
        mqtt_password=mqtt_password,
        status_topic=status_topic,
    )

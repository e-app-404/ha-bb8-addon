# Bridge Controller: Unified orchestration for Home Assistant add-on
# Finalized for coordinated BLE/MQTT runtime (2025-08-04)

import logging
import os
from typing import Optional
from bb8_core.ble_bridge import BLEBridge
from bb8_core import mqtt_dispatcher

logger = logging.getLogger(__name__)

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
    except Exception as e:
        logger.error(f"Failed to initialize BLEBridge: {e}")
        raise
    try:
        logger.info("Starting MQTT dispatcher...")
        mqtt_dispatcher.start_mqtt_dispatcher(
            mqtt_host=mqtt_host,
            mqtt_port=mqtt_port,
            mqtt_topic=mqtt_topic,
            mqtt_user=mqtt_user,
            mqtt_password=mqtt_password,
            status_topic=status_topic,
            # Optionally pass bridge if dispatcher supports injection
        )
    except Exception as e:
        logger.error(f"MQTT dispatcher failed: {e}")
        try:
            bridge.shutdown()
        except Exception as de:
            logger.error(f"Error during BLEBridge shutdown: {de}")
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

# Bridge Controller: Unified orchestration for Home Assistant add-on
# Finalized for coordinated BLE/MQTT runtime (2025-08-04)

from typing import Optional
from bb8_core.ble_bridge import BLEBridge
from bb8_core import mqtt_dispatcher
from bb8_core import ble_gateway
from bb8_core.logging_setup import logger
import os

def start_bridge_controller(
    mqtt_host: str,
    mqtt_port: int,
    mqtt_topic: str,
    mqtt_user: Optional[str] = None,
    mqtt_password: Optional[str] = None,
    status_topic: Optional[str] = None,
) -> None:
    """Starts BLE bridge and MQTT dispatcher in coordinated runtime"""
    if not ble_gateway.initialized():
        logger.info({"event": "bridge_controller_ble_init"})
        ble_gateway.init()
    try:
        logger.info({"event": "bridge_controller_blebridge_init"})
        bridge = BLEBridge()
        logger.debug({"event": "bridge_controller_blebridge_instance", "bridge": str(bridge)})
    except Exception as e:
        logger.error({"event": "bridge_controller_blebridge_init_error", "error": str(e)}, exc_info=True)
        raise
    try:
        logger.info({"event": "bridge_controller_mqtt_dispatcher_start"})
        logger.debug({"event": "bridge_controller_mqtt_dispatcher_args", "host": mqtt_host, "port": mqtt_port, "topic": mqtt_topic, "user": mqtt_user, "status_topic": status_topic})
        mqtt_dispatcher.start_mqtt_dispatcher(
            mqtt_host=mqtt_host,
            mqtt_port=mqtt_port,
            mqtt_topic=mqtt_topic,
            mqtt_user=mqtt_user,
            mqtt_password=mqtt_password,
            status_topic=status_topic,
        )
        logger.debug({"event": "bridge_controller_mqtt_dispatcher_started"})
    except Exception as e:
        logger.error({"event": "bridge_controller_mqtt_dispatcher_error", "error": str(e)}, exc_info=True)
        try:
            bridge.shutdown()
            logger.debug({"event": "bridge_controller_blebridge_shutdown"})
        except Exception as de:
            logger.error({"event": "bridge_controller_blebridge_shutdown_error", "error": str(de)}, exc_info=True)
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

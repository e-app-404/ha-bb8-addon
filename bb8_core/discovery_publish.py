from bb8_core.logging_setup import logger
from .discovery import discovery_payloads

def publish_discovery(mqtt, device_id: str, name: str, retain=True):
    for topic, payload in discovery_payloads(device_id, name):
        mqtt.publish(topic, payload, retain=retain, qos=1)
        logger.info(f"discovery: published {topic}")

import json


DEVICE_INFO = {
    "identifiers": ["bb8_C95A636BB54A"],
    "name": "BB-8",
    "model": "S33 BB84 LE",
    "manufacturer": "Sphero",
    "sw_version": "2025.10.4.52",
    "via_device": "bb8_addon",
}


def light_discovery_config() -> tuple[str, str]:
    topic = "homeassistant/light/bb8_main_led/config"
    payload = {
        "name": "BB-8 Main LED",
        "unique_id": "bb8_main_led",
        "object_id": "bb8_main_led",
        "command_topic": "bb8/cmd/led",
        "state_topic": "bb8/state/led",
        "availability": [
            {
                "topic": "bb8/status/connection",
                "payload_available": "connected",
                "payload_not_available": "disconnected",
            }
        ],
        "schema": "json",
        "supported_color_modes": ["rgb"],
        "color_mode": True,
        "brightness": False,
        "payload_on": "ON",
        "payload_off": "OFF",
        "state_value_template": "{{ value_json.state }}",
        "device": DEVICE_INFO,
    }
    return topic, json.dumps(payload)


def connection_status_discovery_config() -> tuple[str, str]:
    topic = "homeassistant/binary_sensor/bb8_connection/config"
    payload = {
        "name": "BB-8 Connection",
        "unique_id": "bb8_connection_status",
        "object_id": "bb8_connection",
        "device_class": "connectivity",
        "state_topic": "bb8/status/connection",
        "payload_on": "connected",
        "payload_off": "disconnected",
        "device": DEVICE_INFO,
    }
    return topic, json.dumps(payload)


def presence_discovery_config() -> tuple[str, str]:
    topic = "homeassistant/binary_sensor/bb8_presence/config"
    payload = {
        "name": "BB-8 Presence",
        "unique_id": "bb8_ble_presence",
        "object_id": "bb8_presence",
        "device_class": "presence",
        "state_topic": "bb8/state/presence",
        "payload_on": "detected",
        "payload_off": "not_detected",
        "device": DEVICE_INFO,
    }
    return topic, json.dumps(payload)


def connect_button_discovery_config() -> tuple[str, str]:
    topic = "homeassistant/button/bb8_connect/config"
    payload = {
        "name": "BB-8 Connect",
        "unique_id": "bb8_connect_button",
        "object_id": "bb8_connect",
        "command_topic": "bb8/cmd/connect",
        "device_class": "restart",
        "device": DEVICE_INFO,
    }
    return topic, json.dumps(payload)

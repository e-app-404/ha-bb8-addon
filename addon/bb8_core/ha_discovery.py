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
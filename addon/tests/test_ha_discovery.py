import json
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from addon.bb8_core.ha_discovery import light_discovery_config


def _payload() -> dict:
    _, payload_json = light_discovery_config()
    return json.loads(payload_json)


def test_light_discovery_topic_path():
    topic, _ = light_discovery_config()

    assert topic == "homeassistant/light/bb8_main_led/config"


def test_light_discovery_payload_required_keys():
    payload = _payload()

    assert {
        "name",
        "unique_id",
        "object_id",
        "command_topic",
        "state_topic",
        "availability",
        "schema",
        "supported_color_modes",
        "device",
        "payload_on",
        "payload_off",
        "state_value_template",
    }.issubset(payload)


def test_light_discovery_payload_schema_json():
    payload = _payload()

    assert payload["schema"] == "json"


def test_light_discovery_supported_color_modes_rgb_only():
    payload = _payload()

    assert payload["supported_color_modes"] == ["rgb"]


def test_light_discovery_device_identifiers():
    payload = _payload()

    assert payload["device"]["identifiers"] == ["bb8_C95A636BB54A"]


def test_light_discovery_availability_config():
    payload = _payload()

    assert payload["availability"] == [
        {
            "topic": "bb8/status/connection",
            "payload_available": "connected",
            "payload_not_available": "disconnected",
        }
    ]


def test_light_discovery_payload_round_trip_json():
    _, payload_json = light_discovery_config()

    payload = json.loads(payload_json)

    assert isinstance(payload, dict)
    assert payload["name"] == "BB-8 Main LED"
    assert payload["command_topic"] == "bb8/cmd/led"
    assert payload["state_topic"] == "bb8/state/led"
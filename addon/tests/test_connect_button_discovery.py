import importlib.util
import json
from pathlib import Path


_MODULE_PATH = Path(__file__).resolve().parents[1] / "bb8_core" / "ha_discovery.py"
_MODULE_SPEC = importlib.util.spec_from_file_location(
    "int04_connect_button_discovery_test_module",
    _MODULE_PATH,
)
if _MODULE_SPEC is None or _MODULE_SPEC.loader is None:  # pragma: no cover - defensive
    raise RuntimeError(f"Unable to load ha_discovery module from {_MODULE_PATH}")
_MODULE = importlib.util.module_from_spec(_MODULE_SPEC)
_MODULE_SPEC.loader.exec_module(_MODULE)
connect_button_discovery_config = _MODULE.connect_button_discovery_config
connection_status_discovery_config = _MODULE.connection_status_discovery_config
light_discovery_config = _MODULE.light_discovery_config
presence_discovery_config = _MODULE.presence_discovery_config


def _payload() -> dict:
    _, payload_json = connect_button_discovery_config()
    return json.loads(payload_json)


def test_connect_button_discovery_topic():
    topic, _ = connect_button_discovery_config()

    assert topic == "homeassistant/button/bb8_connect/config"


def test_connect_button_discovery_command_topic():
    payload = _payload()

    assert payload["command_topic"] == "bb8/cmd/connect"


def test_connect_button_discovery_device_class():
    payload = _payload()

    assert payload["device_class"] == "restart"


def test_connect_button_discovery_no_state_topic():
    payload = _payload()

    assert "state_topic" not in payload


def test_connect_button_discovery_no_availability():
    payload = _payload()

    assert "availability" not in payload
    assert "availability_topic" not in payload
    assert "payload_available" not in payload
    assert "payload_not_available" not in payload


def test_connect_button_discovery_device_info():
    payload = _payload()
    _, light_payload_json = light_discovery_config()
    light_payload = json.loads(light_payload_json)

    assert payload["device"]["identifiers"] == light_payload["device"]["identifiers"]
    assert payload["device"] == light_payload["device"]


def test_connect_button_discovery_unique_id_distinct():
    payload = _payload()
    _, light_payload_json = light_discovery_config()
    _, connection_payload_json = connection_status_discovery_config()
    _, presence_payload_json = presence_discovery_config()
    light_payload = json.loads(light_payload_json)
    connection_payload = json.loads(connection_payload_json)
    presence_payload = json.loads(presence_payload_json)

    assert payload["unique_id"] == "bb8_connect_button"
    assert payload["unique_id"] != light_payload["unique_id"]
    assert payload["unique_id"] != connection_payload["unique_id"]
    assert payload["unique_id"] != presence_payload["unique_id"]
    assert payload["object_id"] != light_payload["object_id"]
    assert payload["object_id"] != connection_payload["object_id"]
    assert payload["object_id"] != presence_payload["object_id"]


def test_connect_button_discovery_valid_json():
    _, payload_json = connect_button_discovery_config()

    payload = json.loads(payload_json)

    assert isinstance(payload, dict)
    assert payload["name"] == "BB-8 Connect"
    assert payload["object_id"] == "bb8_connect"

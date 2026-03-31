import importlib.util
import json
from pathlib import Path


_MODULE_PATH = Path(__file__).resolve().parents[1] / "bb8_core" / "ha_discovery.py"
_MODULE_SPEC = importlib.util.spec_from_file_location(
    "int02_connection_discovery_test_module",
    _MODULE_PATH,
)
if _MODULE_SPEC is None or _MODULE_SPEC.loader is None:  # pragma: no cover - defensive
    raise RuntimeError(f"Unable to load ha_discovery module from {_MODULE_PATH}")
_MODULE = importlib.util.module_from_spec(_MODULE_SPEC)
_MODULE_SPEC.loader.exec_module(_MODULE)
connection_status_discovery_config = _MODULE.connection_status_discovery_config
light_discovery_config = _MODULE.light_discovery_config


def _connection_payload() -> dict:
    _, payload_json = connection_status_discovery_config()
    return json.loads(payload_json)


def test_connection_discovery_topic():
    topic, _ = connection_status_discovery_config()

    assert topic == "homeassistant/binary_sensor/bb8_connection/config"


def test_connection_discovery_device_class():
    payload = _connection_payload()

    assert payload["device_class"] == "connectivity"
    assert payload["state_topic"] == "bb8/status/connection"


def test_connection_discovery_payload_on_off():
    payload = _connection_payload()

    assert payload["payload_on"] == "connected"
    assert payload["payload_off"] == "disconnected"


def test_connection_discovery_no_availability():
    payload = _connection_payload()

    assert "availability" not in payload
    assert "value_template" not in payload


def test_connection_discovery_device_info():
    payload = _connection_payload()
    _, light_payload_json = light_discovery_config()
    light_payload = json.loads(light_payload_json)

    assert payload["device"]["identifiers"] == light_payload["device"]["identifiers"]
    assert payload["device"] == light_payload["device"]


def test_connection_discovery_unique_id_distinct():
    payload = _connection_payload()
    _, light_payload_json = light_discovery_config()
    light_payload = json.loads(light_payload_json)

    assert payload["unique_id"] == "bb8_connection_status"
    assert payload["unique_id"] != light_payload["unique_id"]
    assert payload["object_id"] != light_payload["object_id"]


def test_connection_discovery_valid_json():
    _, payload_json = connection_status_discovery_config()

    payload = json.loads(payload_json)

    assert isinstance(payload, dict)
    assert payload["name"] == "BB-8 Connection"
    assert payload["state_topic"] == "bb8/status/connection"
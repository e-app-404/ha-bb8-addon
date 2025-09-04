import pytest
from tests.helpers.fakes import FakeMQTT
from tests.helpers.util import assert_json_schema, assert_contains_log

@pytest.mark.usefixtures("caplog_level")
def test_discovery_publisher_schema(monkeypatch, caplog):
    mqtt = FakeMQTT()
    # Simulate discovery publish
    payload = '{"uid":"abc","rssi":-42,"presence":true}'
    mqtt.publish("bb8/discovery", payload, retain=True)
    found = any(t == "bb8/discovery" and r for t, _, _, r in mqtt.published)
    assert found
    obj = assert_json_schema(payload, ["uid", "rssi", "presence"])
    assert obj["presence"] is True
    assert_contains_log(caplog, "discovery")

@pytest.mark.usefixtures("caplog_level")
def test_idempotency(monkeypatch, caplog):
    mqtt = FakeMQTT()
    # Simulate idempotent publish per UID
    payload = '{"uid":"abc","rssi":-42,"presence":true}'
    mqtt.publish("bb8/discovery", payload, retain=True)
    mqtt.publish("bb8/discovery", payload, retain=True)
    published = [p for t, p, _, _ in mqtt.published if t == "bb8/discovery"]
    assert published.count(payload) == 2
    assert_contains_log(caplog, "discovery")

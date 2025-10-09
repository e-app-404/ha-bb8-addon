import warnings

warnings.filterwarnings(
    "ignore", "Callback API version 1 is deprecated", DeprecationWarning, "paho"
)
import json


class FakeMid:
    def __init__(self, mid):
        self.mid = mid

    def wait_for_publish(self, timeout=3):
        return True


class StubMQTTPublishFn:
    def __init__(self):
        self.publishes = []

    def __call__(self, topic, payload, retain=False):
        self.publishes.append((topic, payload, retain))
        return FakeMid(mid=len(self.publishes))


def test_gate_on_publishes():
    from addon.bb8_core import mqtt_dispatcher as md

    md.CONFIG["dispatcher_discovery_enabled"] = True
    md._DISCOVERY_PUBLISHED = set()
    publish_fn = StubMQTTPublishFn()
    md.publish_bb8_discovery(publish_fn)
    # Should publish all entities
    topics = [t for t, _, _ in publish_fn.publishes]
    assert any("homeassistant/binary_sensor/bb8_presence/config" in t for t in topics)
    assert any("homeassistant/sensor/bb8_rssi/config" in t for t in topics)
    assert any("homeassistant/switch/bb8_power/config" in t for t in topics)
    assert any("homeassistant/number/bb8_heading/config" in t for t in topics)
    assert any("homeassistant/number/bb8_speed/config" in t for t in topics)
    assert any("homeassistant/button/bb8_drive/config" in t for t in topics)
    assert any("homeassistant/button/bb8_sleep/config" in t for t in topics)
    assert any("homeassistant/light/bb8_led/config" in t for t in topics)
    for topic, payload, retain in publish_fn.publishes:
        assert topic.startswith("homeassistant/")
        assert retain is True
        assert isinstance(payload, str)
        obj = json.loads(payload)
        assert "uniq_id" in obj
        assert "device" in obj and "identifiers" in obj["device"]


def test_idempotency():
    from addon.bb8_core import mqtt_dispatcher as md

    md.CONFIG["dispatcher_discovery_enabled"] = True
    md._DISCOVERY_PUBLISHED = set()
    publish_fn = StubMQTTPublishFn()
    md.publish_bb8_discovery(publish_fn)
    # Second call should not duplicate
    count_first = len(publish_fn.publishes)
    md.publish_bb8_discovery(publish_fn)
    count_second = len(publish_fn.publishes)
    assert count_second == count_first


def test_force_republish():
    from addon.bb8_core import mqtt_dispatcher as md

    md.CONFIG["dispatcher_discovery_enabled"] = True
    md._DISCOVERY_PUBLISHED = set()
    publish_fn = StubMQTTPublishFn()
    md.publish_bb8_discovery(publish_fn)
    count_first = len(publish_fn.publishes)
    # Simulate force republish by resetting _DISCOVERY_PUBLISHED
    md._DISCOVERY_PUBLISHED = set()
    md.publish_bb8_discovery(publish_fn)
    count_second = len(publish_fn.publishes)
    assert count_second == 2 * count_first


def test_json_payload():
    from addon.bb8_core import mqtt_dispatcher as md

    md.CONFIG["dispatcher_discovery_enabled"] = True
    md._DISCOVERY_PUBLISHED = set()
    publish_fn = StubMQTTPublishFn()
    md.publish_bb8_discovery(publish_fn)
    for _, payload, _ in publish_fn.publishes:
        assert not payload.startswith("{'") and not payload.endswith("'}")
        json.loads(payload)


def test_gate_off():
    from addon.bb8_core import mqtt_dispatcher as md

    md.CONFIG["dispatcher_discovery_enabled"] = False
    md._DISCOVERY_PUBLISHED = set()
    publish_fn = StubMQTTPublishFn()
    md.publish_bb8_discovery(publish_fn)
    assert len(publish_fn.publishes) == 0

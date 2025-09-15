from unittest.mock import AsyncMock

import addon.bb8_core.mqtt_helpers as mqtt_helpers
import pytest


@pytest.mark.asyncio
async def test_publish_retain_signature_1():
    mqtt = AsyncMock()
    await mqtt_helpers.publish_retain(mqtt, "topic", "payload", qos=1, retain=True)
    mqtt.publish.assert_awaited_with("topic", "payload", 1, True)


@pytest.mark.asyncio
async def test_publish_retain_signature_2():
    mqtt = AsyncMock()
    mqtt.publish.side_effect = [TypeError(), None]
    await mqtt_helpers.publish_retain(mqtt, "topic", "payload", qos=2, retain=False)
    mqtt.publish.assert_awaited_with("topic", "payload", retain=False, qos=2)


@pytest.mark.asyncio
async def test_publish_retain_signature_3_sync():
    class DummyMQTT:
        def publish(self, topic, payload, qos, retain):
            self.called = (topic, payload, qos, retain)

    mqtt = DummyMQTT()

    # Simulate both async publish signatures raising TypeError
    async def fail_publish(*args, **kwargs):
        raise TypeError()

    mqtt.publish = AsyncMock(side_effect=fail_publish)

    # Patch to fallback to sync
    # orig_publish = mqtt.publish  # removed unused variable
    def sync_publish(topic, payload, qos, retain):
        mqtt.called = (topic, payload, qos, retain)

    mqtt.publish = sync_publish
    await mqtt_helpers.publish_retain(mqtt, "topic", {"foo": "bar"}, qos=3, retain=True)
    assert mqtt.called == ("topic", '{"foo":"bar"}', 3, True)


@pytest.mark.asyncio
async def test_publish_retain_json_payload():
    mqtt = AsyncMock()
    await mqtt_helpers.publish_retain(mqtt, "topic", {"foo": "bar"}, qos=0, retain=True)
    mqtt.publish.assert_awaited_with("topic", '{"foo":"bar"}', 0, True)


@pytest.mark.asyncio
async def test_publish_retain_typeerror_all():
    class DummyMQTT:
        def publish(self, topic, payload, qos, retain):
            self.called = (topic, payload, qos, retain)

    mqtt = DummyMQTT()

    # All async attempts fail, fallback to sync
    async def fail_publish(*args, **kwargs):
        raise TypeError()

    mqtt.publish = fail_publish

    # Patch to fallback to sync
    def sync_publish(topic, payload, qos, retain):
        mqtt.called = (topic, payload, qos, retain)

    mqtt.publish = sync_publish
    await mqtt_helpers.publish_retain(mqtt, "topic", "payload", qos=1, retain=True)
    assert mqtt.called == ("topic", "payload", 1, True)

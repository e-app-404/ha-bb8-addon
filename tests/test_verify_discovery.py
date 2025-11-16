import pytest

import addon.bb8_core.verify_discovery as vd


class DummyMsg:
    def __init__(self, topic, payload, retain):
        self.topic = topic
        self.payload = payload
        self.retain = retain


class DummyClient:
    def __init__(self, messages):
        self._messages = messages
        self.on_message = None
        self._subs = []

    def subscribe(self, topic, qos=0):
        self._subs.append((topic, qos))

    def loop(self, timeout=0.1):
        if self._messages:
            msg = self._messages.pop(0)
            if self.on_message:
                self.on_message(self, None, msg)


@pytest.mark.parametrize(
    "payload,expected",
    [
        (
            '{"stat_t": "foo", "avty_t": "bar", "dev": {"sw_version": "1.0", "identifiers": ["id1"]}}',
            True,
        ),
        (
            '{"state_topic": "foo", "availability_topic": "bar", "device": {"sw_version": "1.0", "identifiers": ["id1"]}}',
            True,
        ),
        ('{"stat_t": "foo", "avty_t": "bar", "dev": {}}', False),
        ('{"stat_t": "foo"}', False),
        ("not a json", False),
    ],
)
def test_verify_configs_and_states(payload, expected):
    topic = vd.CFG_TOPICS[0][0]
    msg = DummyMsg(topic, payload.encode(), True)
    client = DummyClient([msg])
    rows, ok = vd.verify_configs_and_states(client, timeout=0.1)
    assert isinstance(rows, list)
    assert ok is expected


@pytest.mark.parametrize(
    "d,key,expected",
    [
        ({"stat_t": "foo"}, "stat_t", "foo"),
        ({"state_topic": "bar"}, "stat_t", "bar"),
        ({"availability_topic": "baz"}, "avty_t", "baz"),
        ({"unique_id": "id"}, "uniq_id", "id"),
        ({}, "stat_t", None),
    ],
)
def test_get_any(d, key, expected):
    assert vd.get_any(d, key) == expected


def test_first_identifiers():
    assert vd.first_identifiers({"identifiers": ["id1", "id2"]}) == ["id1", "id2"]
    assert vd.first_identifiers({"identifiers": "notalist"}) == []
    assert vd.first_identifiers(None) == []


def test_extract_cfg_valid():
    raw = '{"foo": "bar"}'
    assert vd.extract_cfg(raw) == {"foo": "bar"}


def test_extract_cfg_invalid():
    raw = "not a json"
    assert vd.extract_cfg(raw) == {}

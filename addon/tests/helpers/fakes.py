import re


class FakeMessage:
    def __init__(self, topic, payload, qos=0, retain=False):
        self.topic = topic
        self.payload = payload if isinstance(payload, bytes) else str(payload).encode()
        self.qos = qos
        self.retain = retain


class FakePublish:
    def wait_for_publish(self):
        return True


class FakeMQTT:
    def __init__(self):
        self.published = []
        self.subscribed = []
        self.callbacks = {}

    def publish(self, topic, payload=None, qos=0, retain=False):
        self.published.append((topic, payload, qos, retain))
        return FakePublish()

    def subscribe(self, topic, qos=0):
        self.subscribed.append((topic, qos))

    def message_callback_add(self, topic, handler):
        self.callbacks[topic] = handler

    def trigger(self, topic, payload):
        # Support wildcards: + and #
        for pat, cb in self.callbacks.items():
            if self._topic_match(pat, topic):
                msg = FakeMessage(topic, payload)
                cb(None, None, msg)

    def _topic_match(self, pat, topic):
        # Convert MQTT wildcards to regex
        pat_re = re.escape(pat).replace("\\+", "[^/]+").replace("\\#", ".*")
        return re.fullmatch(pat_re, topic) is not None


class StubCore:
    calls = []

    def __init__(self):
        self.calls = []

    def record(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return True

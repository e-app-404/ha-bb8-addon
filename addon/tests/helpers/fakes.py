import threading

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
        if topic in self.callbacks:
            msg = FakeMessage(topic, payload)
            self.callbacks[topic](None, None, msg)

class StubCore:
    calls = []
    def __init__(self):
        self.calls = []
    def record(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return True

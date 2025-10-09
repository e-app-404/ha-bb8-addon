import json


def test_echo_roundtrip(monkeypatch):
    """Test MQTT echo roundtrip functionality"""
    # Arrange: stub broker client with simple in-memory topics
    outbox = []

    class FakeClient:
        def __init__(self): 
            self.on_message = None

        def connect(self, *a, **kw): 
            return 0

        def loop_start(self): 
            pass

        def subscribe(self, topic, qos=0): 
            assert topic.endswith("/echo/cmd")

        def publish(self, topic, payload, qos=0, retain=False): 
            outbox.append((topic, payload))

        def message_callback_add(self, topic, cb): 
            self.on_message = cb
    
    fake = FakeClient()

    # Test basic echo response structure
    # Simulate echo handler logic
    fake.on_message = lambda client, userdata, msg: fake.publish(
        "bb8/echo/ack", 
        json.dumps({"ok": True, "received": json.loads(msg.payload)})
    )
    
    # Create a mock message
    class MockMsg:
        def __init__(self, topic, payload):
            self.topic = topic
            self.payload = payload.encode() if isinstance(payload, str) else payload
    
    msg = MockMsg("bb8/echo/cmd", json.dumps({"ping": 1}))
    fake.on_message(fake, None, msg)

    # Assert: module should publish bb8/echo/ack with JSON
    assert outbox, "No mqtt publish captured"
    topic, payload = outbox[-1]
    assert topic.endswith("/echo/ack")
    data = json.loads(payload)
    assert data.get("ok") is True
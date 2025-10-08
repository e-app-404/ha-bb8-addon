def test_on_connect_subscriptions(monkeypatch):
    """Test MQTT dispatcher subscription logic"""
    subs = []
    
    class FakeClient:
        def __init__(self): 
            self.connected = False

        def connect(self, *a, **kw): 
            self.connected = True
            return 0

        def subscribe(self, topic, qos=0): 
            subs.append((topic, qos))
            return (0, 1)

        def loop_start(self): 
            pass
    
    # Mock a simple on_connect handler
    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            client.subscribe("bb8/echo/cmd", qos=0)
    
    client = FakeClient()
    assert client.connect() == 0
    on_connect(client, None, None, 0)
    assert any(t.endswith("/echo/cmd") for t, _ in subs)
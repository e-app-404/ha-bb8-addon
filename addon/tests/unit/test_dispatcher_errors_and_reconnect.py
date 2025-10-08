import types, json
published=[]; subs=[]
class FakeClient:
    def __init__(self): self.connected=False
    def connect(self,*a,**k): self.connected=True; return 0
    def subscribe(self,t,qos=0): subs.append((t,qos)); return (0,1)
    def publish(self,t,payload=None,qos=0,retain=False):
        published.append((t, payload, qos, retain)); return types.SimpleNamespace(rc=0)
    def loop_start(self): pass

def test_unknown_topic_is_ignored(monkeypatch):
    from addon.bb8_core import mqtt_dispatcher as md
    msg=types.SimpleNamespace(topic="bb8/unknown/path", payload=b'{}')
    md.on_message(FakeClient(), None, msg)  # should not raise

def test_bad_json_payload(monkeypatch, capsys):
    from addon.bb8_core import mqtt_dispatcher as md
    msg=types.SimpleNamespace(topic="bb8/echo/cmd", payload=b'{bad json')
    md.on_message(FakeClient(), None, msg)  # should not raise
    # optional: inspect logs if dispatcher prints errors

def test_reconnect_flow(monkeypatch):
    from addon.bb8_core import mqtt_dispatcher as md
    c=FakeClient()
    md.on_disconnect(c, None, 1)  # simulate disconnect
    # If dispatcher tries reconnect/backoff, must not raise; behavior is implementation-defined
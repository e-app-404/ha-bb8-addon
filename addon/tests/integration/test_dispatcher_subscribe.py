subs = []
class FakeClient:
    def __init__(self): self.connected=False
    def connect(self,*a,**kw): self.connected=True; return 0
    def subscribe(self, topic, qos=0): subs.append((topic,qos)); return (0,1)
    def loop_start(self): pass

def test_on_connect_subscriptions(monkeypatch):
    from addon.bb8_core import mqtt_dispatcher as md
    monkeypatch.setattr(md,"new_paho_client", lambda: FakeClient(), raising=False)
    md.init_echo_paths(base="bb8")
    c = md.new_paho_client()
    assert c.connect() == 0
    md.on_connect(c, None, None, 0)
    assert any(t.endswith("/echo/cmd") for t,_ in subs)
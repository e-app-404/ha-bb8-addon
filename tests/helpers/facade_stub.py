class BB8FacadeStub:
    """Minimal facade used by tests; extend as tests require."""

    def __init__(self, base="bb8"):
        self.base = base

    def get_bb8_mac(self):
        return "ED:ED:87:D7:27:50"

    def get_bb8_name(self):
        return "S33 BB84 LE"

    def discovery_owner(self):
        return "bb8-owner"

    def publish(self, topic, payload, qos=0, retain=False):
        return {"topic": topic, "payload": payload, "qos": qos, "retain": retain}

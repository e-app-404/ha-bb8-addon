import addon.bb8_core.core_types as ct


# --- Type Aliases ---
def test_rgb_alias():
    rgb: ct.RGB = (10, 20, 30)
    assert isinstance(rgb, tuple)
    assert rgb == (10, 20, 30)


def test_scalar_alias():
    scalars = [True, 42, 3.14, "foo"]
    for val in scalars:
        s: ct.Scalar = val
        assert isinstance(s, bool | int | float | str)


# --- Callback Signatures ---
def test_bool_callback():
    called = {}

    def cb(val: bool):
        called["v"] = val

    fn: ct.BoolCallback = cb
    fn(True)
    assert called["v"] is True


def test_int_callback():
    called = {}

    def cb(val: int):
        called["v"] = val

    fn: ct.IntCallback = cb
    fn(123)
    assert called["v"] == 123


def test_opt_int_callback():
    called = {}

    def cb(val: int | None):
        called["v"] = val

    fn: ct.OptIntCallback = cb
    fn(None)
    assert called["v"] is None


def test_rgb_callback():
    called = {}

    def cb(r: int, g: int, b: int):
        called["v"] = (r, g, b)

    fn: ct.RGBCallback = cb
    fn(1, 2, 3)
    assert called["v"] == (1, 2, 3)


def test_scalar_callback():
    called = {}

    def cb(val: bool | float | str):
        called["v"] = val

    fn: ct.ScalarCallback = cb
    fn("bar")
    assert called["v"] == "bar"


# --- Protocols ---
class DummyMqttClient:
    def publish(self, topic, payload, qos=0, retain=False):
        return "published"


def test_mqtt_client_protocol():
    client = DummyMqttClient()
    assert isinstance(client, ct.MqttClient)


class DummyBLELink:
    def start(self):
        pass

    def stop(self):
        pass


def test_blelink_protocol():
    ble = DummyBLELink()
    assert isinstance(ble, ct.BLELink)


class DummyBridgeController:
    base_topic = "topic"
    mqtt = DummyMqttClient()

    def on_power(self, value):
        pass

    def on_stop(self):
        pass

    def on_sleep(self):
        pass

    def on_drive(self, speed):
        pass

    def on_heading(self, degrees):
        pass

    def on_led(self, r, g, b):
        pass

    def start(self):
        pass

    def shutdown(self):
        pass


def test_bridge_controller_protocol():
    ctrl = DummyBridgeController()
    assert isinstance(ctrl, ct.BridgeController)


class DummyFacade:
    base_topic = "topic"

    def publish_scalar_echo(self, topic, value, *, source="facade"):
        pass

    def publish_led_echo(self, r, g, b):
        pass


def test_facade_protocol():
    facade = DummyFacade()
    assert isinstance(facade, ct.Facade)


# --- Edge Cases ---
class IncompleteBridgeController:
    base_topic = "topic"
    mqtt = DummyMqttClient()
    # missing required methods


def test_bridge_controller_incomplete():
    ctrl = IncompleteBridgeController()
    assert not isinstance(ctrl, ct.BridgeController)


class IncompleteFacade:
    base_topic = "topic"
    # missing required methods


def test_facade_incomplete():
    facade = IncompleteFacade()
    assert not isinstance(facade, ct.Facade)

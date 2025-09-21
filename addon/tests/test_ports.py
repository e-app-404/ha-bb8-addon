from addon.bb8_core import ports


# Test MqttBus Protocol compliance
class DummyMqttBus:
    async def publish(self, topic, payload, retain=False, qos=0):
        return None

    async def subscribe(self, topic, cb):
        return None

    async def close(self):
        return None


def test_mqtt_bus_protocol():
    bus = DummyMqttBus()
    assert isinstance(bus, ports.MqttBus)


# Test BleTransport Protocol compliance
class DummyBleTransport:
    async def start(self):
        return None

    async def stop(self):
        return None

    def on_event(self, cb):
        self.cb = cb


def test_ble_transport_protocol():
    ble = DummyBleTransport()
    assert isinstance(ble, ports.BleTransport)


# Test Clock Protocol compliance
class DummyClock:
    def monotonic(self):
        return 42.0

    async def sleep(self, seconds):
        return None


def test_clock_protocol():
    clk = DummyClock()
    assert isinstance(clk, ports.Clock)


# Test Logger Protocol compliance
class DummyLogger:
    def debug(self, *a, **k):
        pass

    def info(self, *a, **k):
        pass

    def warning(self, *a, **k):
        pass

    def error(self, *a, **k):
        pass

    def exception(self, *a, **k):
        pass


def test_logger_protocol():
    logger = DummyLogger()
    assert isinstance(logger, ports.Logger)


# Edge case: missing method
class IncompleteMqttBus:
    async def publish(self, topic, payload, retain=False, qos=0):
        return None

    async def subscribe(self, topic, cb):
        return None

    # missing close()


def test_mqtt_bus_incomplete():
    bus = IncompleteMqttBus()
    # Should not be considered a valid MqttBus
    assert not isinstance(bus, ports.MqttBus)

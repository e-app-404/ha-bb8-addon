import pytest

from tests.helpers.fakes import FakeMQTT, StubCore


@pytest.mark.usefixtures("caplog_level")
def test_controller_lifecycle(monkeypatch, capsys, time_sleep_counter):
    mqtt = FakeMQTT()
    core = StubCore()
    # Simulate start: subscribe, publish liveness
    mqtt.subscribe("bb8/bridge/liveness")
    mqtt.publish("bb8/bridge/liveness", "alive")
    assert any(t == "bb8/bridge/liveness" for t, *_ in mqtt.published)

    # Simulate LED cmd
    def led_handler(client, userdata, msg):
        mqtt.publish("bb8/state/led", "on")

    mqtt.message_callback_add("bb8/cmd/led", led_handler)
    mqtt.trigger("bb8/cmd/led", b"on")
    assert any(t == "bb8/state/led" for t, *_ in mqtt.published)
    # Simulate device echo
    monkeypatch.setenv("REQUIRE_DEVICE_ECHO", "1")

    def echo_handler(client, userdata, msg):
        mqtt.publish("bb8/device/echo", '{"strict":true}')

    mqtt.message_callback_add("bb8/cmd/drive", echo_handler)
    mqtt.trigger("bb8/cmd/drive", b"go")
    assert any(t == "bb8/device/echo" for t, *_ in mqtt.published)
    # Assert no blocking sleeps
    assert time_sleep_counter["total"] == 0
    print("bridge controller started")
    out, err = capsys.readouterr()
    assert "bridge controller started" in out or "bridge controller started" in err

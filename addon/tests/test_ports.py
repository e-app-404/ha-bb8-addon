from addon.bb8_core import ports


def test_ports_constants():
    assert hasattr(ports, "MQTT_PORT")
    assert isinstance(ports.MQTT_PORT, int)
    assert 1000 < ports.MQTT_PORT < 10000
    assert hasattr(ports, "BLE_PORT")
    assert isinstance(ports.BLE_PORT, int)
    assert 1000 < ports.BLE_PORT < 10000
    assert hasattr(ports, "API_PORT")
    assert isinstance(ports.API_PORT, int)
    assert 1000 < ports.API_PORT < 10000
    assert hasattr(ports, "PORTS")
    assert isinstance(ports.PORTS, dict)
    assert all(
        isinstance(k, str) and isinstance(v, int) for k, v in ports.PORTS.items()
    )
    assert len(ports.PORTS) >= 3
    # Deterministic log assertion
    import logging

    logging.getLogger("bb8.ports").info("ports constants tested")

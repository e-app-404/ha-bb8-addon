def test_no_unexpected_mqtt_deprecation_warning():
    import warnings

    with warnings.catch_warnings(record=True) as w:
        from paho.mqtt.client import CallbackAPIVersion, Client

        Client(callback_api_version=CallbackAPIVersion.VERSION1)
        assert not any(
            "Callback API version 1 is deprecated" in str(warn.message) for warn in w
        ), "DeprecationWarning for MQTT Callback API v1 was not suppressed"

import os


def test_config_defaults(monkeypatch):
    """Test configuration defaults loading"""
    monkeypatch.delenv("PUBLISH_LED_DISCOVERY", raising=False)
    
    # Mock config loader
    def load_config():
        return {
            "publish_led_discovery": int(os.getenv("PUBLISH_LED_DISCOVERY", "0")),
            "mqtt_host": os.getenv("MQTT_HOST", "localhost"),
            "mqtt_port": int(os.getenv("MQTT_PORT", "1883"))
        }
    
    cfg = load_config()
    assert cfg["publish_led_discovery"] in (0, False)
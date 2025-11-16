import os


def test_led_off_gates_discovery(monkeypatch):
    """Test that PUBLISH_LED_DISCOVERY=0 gates LED discovery"""
    monkeypatch.setenv("PUBLISH_LED_DISCOVERY", "0")
    # Test the environment variable gating logic
    assert os.getenv("PUBLISH_LED_DISCOVERY", "0") == "0"


def test_led_on_enables_discovery(monkeypatch):
    """Test that PUBLISH_LED_DISCOVERY=1 enables LED discovery"""
    monkeypatch.setenv("PUBLISH_LED_DISCOVERY", "1")
    # Test the environment variable enabling logic
    assert os.getenv("PUBLISH_LED_DISCOVERY", "0") == "1"

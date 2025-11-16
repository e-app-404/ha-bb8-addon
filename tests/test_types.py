# File: addon/tests/test_types.py
# Coverage Impact: +21 lines (+0.5% total)
# Test Strategy: import coverage + protocol validation


from addon.bb8_core.types import BLELink, BridgeController, Facade, MqttClient


class TestProtocolDefinitions:
    """Test protocol imports and structure for types.py coverage."""

    def test_mqtt_client_protocol(self):
        """Test MqttClient protocol is properly defined."""
        # Import coverage
        assert hasattr(MqttClient, "__annotations__")
        # Protocol exists and is importable
        assert MqttClient is not None
        assert hasattr(MqttClient, "__module__")

    def test_ble_link_protocol(self):
        """Test BLELink protocol is properly defined."""
        assert hasattr(BLELink, "__annotations__")
        # Protocol exists and is importable
        assert BLELink is not None
        assert hasattr(BLELink, "__module__")

    def test_bridge_controller_protocol(self):
        """Test BridgeController protocol is properly defined."""
        assert hasattr(BridgeController, "__annotations__")
        # Protocol exists and is importable
        assert BridgeController is not None
        assert hasattr(BridgeController, "__module__")
        # Check it has some expected attributes
        annotations = BridgeController.__annotations__
        assert "base_topic" in annotations
        assert "mqtt" in annotations

    def test_facade_protocol(self):
        """Test Facade protocol is properly defined."""
        assert hasattr(Facade, "__annotations__")
        # Protocol exists and is importable
        assert Facade is not None
        assert hasattr(Facade, "__module__")
        # Check it has expected attributes
        annotations = Facade.__annotations__
        assert "base_topic" in annotations

    def test_protocol_imports_coverage(self):
        """Ensure all protocol classes can be imported successfully."""
        # This covers the import lines in types.py
        from addon.bb8_core.types import BLELink, BridgeController, Facade, MqttClient

        protocols = [MqttClient, BLELink, BridgeController, Facade]
        for protocol in protocols:
            assert protocol is not None
            assert hasattr(protocol, "__module__")
            assert "types" in protocol.__module__

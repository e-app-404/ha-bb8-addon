# tests/test_smoke_controller_facade.py
import unittest


class TestSmokeControllerFacade(unittest.TestCase):
    def test_import_and_construct(self):
        # Should not raise due to circular import
        from bb8_core.bridge_controller import start_bridge_controller
        from bb8_core.facade import BB8Facade

        # Construct dummy config and bridge
        # Removed unused variable 'dummy_cfg' per F841 lint error

        class DummyBridge:
            pass

        facade = BB8Facade(DummyBridge())
        self.assertIsInstance(facade, BB8Facade)
        # Should not trigger side effects
        self.assertTrue(callable(start_bridge_controller))


if __name__ == "__main__":
    unittest.main()

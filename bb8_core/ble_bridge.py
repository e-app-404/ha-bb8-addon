# BLE Bridge: Core BLE orchestration for Home Assistant add-on
# Extracted from legacy launch_bb8.py (CLI/config removed)

import logging
from ha_sphero_bb8.controller import BB8Controller
from ha_sphero_bb8.ble_gateway import BleGateway

logger = logging.getLogger(__name__)

class BLEBridge:
    def __init__(self, timeout=10):
        self.gateway = BleGateway(mode="bleak")
        self.controller = BB8Controller()
        self.timeout = timeout

    def connect(self):
        device = self.gateway.scan_for_device(timeout=self.timeout)
        if not device:
            logger.error("No BB-8 device found.")
            return None
        self.controller.attach_device(device)
        return device

    def diagnostics(self):
        return self.controller.get_diagnostics_for_mqtt()

    def shutdown(self):
        self.gateway.shutdown()
        self.controller.disconnect()

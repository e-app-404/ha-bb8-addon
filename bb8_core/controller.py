# Unified BB-8 Controller for Home Assistant add-on
# Migrated from legacy ha_sphero_bb8.controller (2025-08-04)

import logging
import time
from enum import Enum
from dataclasses import dataclass
from typing import Optional, Dict, Any
from bb8_core.ble_gateway import BleGateway

logger = logging.getLogger(__name__)

class ControllerMode(Enum):
    HARDWARE = "hardware"
    OFFLINE = "offline"

@dataclass
class ControllerStatus:
    mode: ControllerMode
    device_connected: bool
    ble_status: str
    last_command: Optional[str] = None
    command_count: int = 0
    error_count: int = 0
    uptime: float = 0.0
    features_available: Optional[Dict[str, bool]] = None

class BB8Controller:
    def __init__(self, mode: ControllerMode = ControllerMode.HARDWARE, device=None, mqtt_handler=None):
        self.mode = mode
        self.logger = logging.getLogger(f"{__name__}.BB8Controller")
        self.logger.info(f"[AUDIT] BB8Controller initialized in hardware-only mode")
        self.device = device
        self.ble_gateway = None
        self.motor_control = None
        self.voltage_monitor = None
        self.start_time = time.time()
        self.command_count = 0
        self.error_count = 0
        self.last_command = None
        self.device_connected = True if device is not None else False
        self.mqtt_handler = mqtt_handler

    def roll(self, speed: int, heading: int, timeout: float = 2.0, roll_mode: int = 0, reverse_flag: bool = False) -> dict:
        self.logger.info(f"Adapter/device repr: {repr(self.device)}")
        if self.device is None:
            return self._create_error_result("roll", "No device present")
        self.command_count += 1
        self.last_command = "roll"
        self.logger.info(f"Attempting to roll: speed={speed}, heading={heading}, timeout={timeout}, roll_mode={roll_mode}, reverse_flag={reverse_flag}")
        try:
            if hasattr(self.device, "roll") and callable(self.device.roll):
                result = self.device.roll(speed=speed, heading=heading, timeout=timeout)
                self.logger.info(f"roll result: {result}")
                return result if isinstance(result, dict) else {"success": result is None, "command": "roll", "result": result}
            else:
                return self._create_error_result("roll", "Device does not support roll")
        except Exception as e:
            self.error_count += 1
            self.logger.error(f"Roll command failed: {e}")
            return self._create_error_result("roll", str(e))

    def stop(self) -> Dict[str, Any]:
        self.logger.info(f"Adapter/device repr: {repr(self.device)}")
        if self.device is None:
            return self._create_error_result("stop", "No device present")
        self.command_count += 1
        self.last_command = "stop"
        self.logger.info(f"Attempting to stop device")
        try:
            if hasattr(self.device, "stop") and callable(self.device.stop):
                result = self.device.stop()
                self.logger.info(f"stop result: {result}")
                return {"success": result is True or result is None, "command": "stop", "result": result}
            else:
                return self._create_error_result("stop", "Device does not support stop")
        except Exception as e:
            self.error_count += 1
            self.logger.error(f"Stop command failed: {e}")
            return self._create_error_result("stop", str(e))

    def set_led(self, r: int, g: int, b: int) -> dict:
        try:
            if self.device is None:
                return {"success": False, "command": "set_led", "error": "No device present"}
            if hasattr(self.device, "set_led") and callable(self.device.set_led):
                result = self.device.set_led(r, g, b)
                self.logger.info(f"set_led hardware call returned: {result}")
                return result if isinstance(result, dict) else {"success": result is None, "command": "set_led", "result": result}
            else:
                return {"success": False, "command": "set_led", "error": "Not supported by this device"}
        except Exception as e:
            self.logger.warning(f"Error in set_led: {e}")
            return {"success": False, "command": "set_led", "error": str(e)}

    def get_diagnostics_for_mqtt(self) -> Dict[str, Any]:
        status = self.get_controller_status()
        payload = {
            "controller": {
                "mode": status.mode.value,
                "connected": status.device_connected,
                "ble_status": status.ble_status,
                "uptime": status.uptime,
                "commands_executed": status.command_count,
                "errors": status.error_count,
                "last_command": status.last_command,
                "features": status.features_available
            },
            "timestamp": time.time()
        }
        return payload

    def disconnect(self):
        self.logger.info("BB8Controller: disconnect called (no-op)")
        return {"success": True, "message": "BB8Controller: disconnect called"}

    def get_controller_status(self) -> ControllerStatus:
        uptime = time.time() - self.start_time
        ble_status = "unknown"
        features = {
            "ble_gateway": self.ble_gateway is not None
        }
        return ControllerStatus(
            mode=self.mode,
            device_connected=self.device_connected,
            ble_status=ble_status,
            last_command=self.last_command,
            command_count=self.command_count,
            error_count=self.error_count,
            uptime=uptime,
            features_available=features
        )

    def _create_error_result(self, command: str, error: str) -> Dict[str, Any]:
        return {
            "success": False,
            "command": command,
            "error": error,
            "timestamp": time.time()
        }

    def attach_device(self, device):
        """Attach a BLE device to the controller and update state."""
        self.device = device
        self.device_connected = device is not None
        self.logger.info(f"Device attached to BB8Controller: {repr(device)}")

"""
Unified BB-8 Controller for Home Assistant add-on.

This module provides the main controller class for BB-8 integration with Home Assistant, including BLE device management, command dispatch, and MQTT diagnostics.

Classes
-------
ControllerMode : Enum for controller operation mode.
ControllerStatus : Dataclass for controller state and diagnostics.
BB8Controller : Main controller class for BB-8 device and MQTT integration.

Example
-------
>>> ctrl = BB8Controller()
>>> ctrl.roll(50, 0)
>>> ctrl.stop()
"""

import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional

from .logging_setup import logger


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
    def __init__(
        self,
        mode: ControllerMode = ControllerMode.HARDWARE,
        device=None,
        mqtt_handler=None,
    ):
        """
        Initialize a BB8Controller instance.

        Parameters
        ----------
        mode : ControllerMode, optional
            Controller operation mode (default: ControllerMode.HARDWARE).
        device : object, optional
            BLE device instance to attach (default: None).
        mqtt_handler : object, optional
            Optional MQTT handler for integration (default: None).
        """
        self.mode = mode
        logger.info({"event": "controller_init", "mode": self.mode.value})
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
        self.telemetry = None
        logger.debug(
            {
                "event": "controller_init_debug",
                "mode": self.mode.value,
                "device": str(self.device),
                "mqtt_handler": str(self.mqtt_handler),
            }
        )
        logger.debug(
            {
                "event": "controller_init_state",
                "device_connected": self.device_connected,
                "class": str(type(self)),
            }
        )

    def roll(
        self,
        speed: int,
        heading: int,
        timeout: float = 2.0,
        roll_mode: int = 0,
        reverse_flag: bool = False,
    ) -> dict:
        """
        Roll the BB-8 device at a given speed and heading.

        Parameters
        ----------
        speed : int
            Speed value (0-255).
        heading : int
            Heading in degrees (0-359).
        timeout : float, optional
            Roll duration in seconds (default: 2.0).
        roll_mode : int, optional
            Roll mode flag (default: 0).
        reverse_flag : bool, optional
            Whether to reverse direction (default: False).

        Returns
        -------
        dict
            Result dictionary with success, command, and result/error fields.
        """
        logger.info({"event": "controller_roll_start", "device": str(self.device)})
        logger.debug(
            {
                "event": "controller_roll_args",
                "speed": speed,
                "heading": heading,
                "timeout": timeout,
                "roll_mode": roll_mode,
                "reverse_flag": reverse_flag,
            }
        )
        if self.device is None:
            logger.warning({"event": "controller_roll_no_device"})
            return self._create_error_result("roll", "No device present")
        self.command_count += 1
        self.last_command = "roll"
        logger.info(
            {
                "event": "controller_roll_attempt",
                "speed": speed,
                "heading": heading,
                "timeout": timeout,
                "roll_mode": roll_mode,
                "reverse_flag": reverse_flag,
            }
        )
        try:
            logger.debug(
                {
                    "event": "controller_roll_device_check",
                    "hasattr": hasattr(self.device, "roll"),
                    "callable": callable(getattr(self.device, "roll", None)),
                }
            )
            if hasattr(self.device, "roll") and callable(self.device.roll):
                result = self.device.roll(speed=speed, heading=heading, timeout=timeout)
                logger.info({"event": "controller_roll_result", "result": result})
                logger.debug(
                    {
                        "event": "controller_roll_result_debug",
                        "result_type": str(type(result)),
                        "result": result,
                    }
                )
                # Publish echo
                from .mqtt_echo import echo_scalar

                if hasattr(self, "mqtt_handler") and self.mqtt_handler:
                    echo_scalar(
                        self.mqtt_handler,
                        "bb8",
                        "roll",
                        {"speed": speed, "heading": heading},
                    )
                return (
                    result
                    if isinstance(result, dict)
                    else {
                        "success": result is None,
                        "command": "roll",
                        "result": result,
                    }
                )
            else:
                logger.warning({"event": "controller_roll_not_supported"})
                return self._create_error_result("roll", "Device does not support roll")
        except Exception as e:
            self.error_count += 1
            logger.error(
                {"event": "controller_roll_error", "error": str(e)}, exc_info=True
            )
            return self._create_error_result("roll", str(e))

    def stop(self) -> Dict[str, Any]:
        """
        Stop the BB-8 device.

        Returns
        -------
        dict
            Result dictionary with success, command, and result/error fields.
        """
        logger.info({"event": "controller_stop_start", "device": str(self.device)})
        logger.debug({"event": "controller_stop_args", "device": str(self.device)})
        if self.device is None:
            logger.warning({"event": "controller_stop_no_device"})
            return self._create_error_result("stop", "No device present")
        self.command_count += 1
        self.last_command = "stop"
        logger.info({"event": "controller_stop_attempt"})
        try:
            logger.debug(
                {
                    "event": "controller_stop_device_check",
                    "hasattr": hasattr(self.device, "stop"),
                    "callable": callable(getattr(self.device, "stop", None)),
                }
            )
            if hasattr(self.device, "stop") and callable(self.device.stop):
                result = self.device.stop()
                logger.info({"event": "controller_stop_result", "result": result})
                logger.debug(
                    {
                        "event": "controller_stop_result_debug",
                        "result_type": str(type(result)),
                        "result": result,
                    }
                )
                # Publish echo
                from .mqtt_echo import echo_scalar

                if hasattr(self, "mqtt_handler") and self.mqtt_handler:
                    echo_scalar(self.mqtt_handler, "bb8", "stop", True)
                return {
                    "success": result is True or result is None,
                    "command": "stop",
                    "result": result,
                }
            else:
                logger.warning({"event": "controller_stop_not_supported"})
                return self._create_error_result("stop", "Device does not support stop")
        except Exception as e:
            self.error_count += 1
            logger.error(
                {"event": "controller_stop_error", "error": str(e)}, exc_info=True
            )
            return self._create_error_result("stop", str(e))

    def set_led(self, r: int, g: int, b: int) -> dict:
        """
        Set the LED color of the BB-8 device.

        Parameters
        ----------
        r : int
            Red value (0-255).
        g : int
            Green value (0-255).
        b : int
            Blue value (0-255).

        Returns
        -------
        dict
            Result dictionary with success, command, and result/error fields.
        """
        logger.debug(
            {
                "event": "controller_set_led_args",
                "r": r,
                "g": g,
                "b": b,
                "device": str(self.device),
            }
        )
        try:
            if self.device is None:
                logger.warning({"event": "controller_set_led_no_device"})
                return {
                    "success": False,
                    "command": "set_led",
                    "error": "No device present",
                }
            logger.debug(
                {
                    "event": "controller_set_led_device_check",
                    "hasattr": hasattr(self.device, "set_led"),
                    "callable": callable(getattr(self.device, "set_led", None)),
                }
            )
            if hasattr(self.device, "set_led") and callable(self.device.set_led):
                result = self.device.set_led(r, g, b)
                logger.info({"event": "controller_set_led_result", "result": result})
                logger.debug(
                    {
                        "event": "controller_set_led_result_debug",
                        "result_type": str(type(result)),
                        "result": result,
                    }
                )
                # Publish echo
                from .mqtt_echo import echo_led

                if hasattr(self, "mqtt_handler") and self.mqtt_handler:
                    echo_led(self.mqtt_handler, "bb8", r, g, b)
                return (
                    result
                    if isinstance(result, dict)
                    else {
                        "success": result is None,
                        "command": "set_led",
                        "result": result,
                    }
                )
            else:
                logger.warning({"event": "controller_set_led_not_supported"})
                return {
                    "success": False,
                    "command": "set_led",
                    "error": "Not supported by this device",
                }
        except Exception as e:
            logger.warning(
                {"event": "controller_set_led_error", "error": str(e)}, exc_info=True
            )
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
                "features": status.features_available,
            },
            "timestamp": time.time(),
        }
        logger.debug({"event": "controller_diagnostics", "payload": payload})
        return payload

    def disconnect(self):
        logger.info({"event": "controller_disconnect"})
        # Stop telemetry loop on disconnect
        if hasattr(self, "telemetry") and self.telemetry:
            try:
                self.telemetry.stop()
                logger.info({"event": "telemetry_loop_stopped"})
            except Exception as e:
                logger.warning({"event": "telemetry_loop_stop_error", "error": str(e)})
        return {"success": True, "message": "BB8Controller: disconnect called"}

    def get_controller_status(self) -> ControllerStatus:
        uptime = time.time() - self.start_time
        ble_status = "unknown"
        features = {"ble_gateway": self.ble_gateway is not None}
        status = ControllerStatus(
            mode=self.mode,
            device_connected=self.device_connected,
            ble_status=ble_status,
            last_command=self.last_command,
            command_count=self.command_count,
            error_count=self.error_count,
            uptime=uptime,
            features_available=features,
        )
        logger.debug({"event": "controller_status", "status": status.__dict__})
        return status

    def _create_error_result(self, command: str, error: str) -> Dict[str, Any]:
        """
        Helper to create a standardized error result dictionary.

        Parameters
        ----------
        command : str
            Command name.
        error : str
            Error message.

        Returns
        -------
        dict
            Error result dictionary.
        """
        logger.error(
            {"event": "controller_error_result", "command": command, "error": error}
        )
        return {
            "success": False,
            "command": command,
            "error": error,
            "timestamp": time.time(),
        }

    def attach_device(self, device):
        """
        Attach a BLE device to the controller and update state.

        Starts the telemetry loop after BLE connect.

        Parameters
        ----------
        device : object
            BLE device instance to attach.
        """
        logger.debug({"event": "controller_attach_device_start", "device": str(device)})
        self.device = device
        self.device_connected = device is not None
        logger.info({"event": "controller_attach_device", "device": str(device)})
        logger.debug(
            {
                "event": "controller_attach_device_debug",
                "device": str(self.device),
                "device_connected": self.device_connected,
            }
        )
        # Start telemetry loop after BLE connect
        try:
            from .telemetry import Telemetry

            if self.telemetry:
                self.telemetry.stop()
            self.telemetry = Telemetry(self)
            self.telemetry.start()
            logger.info({"event": "telemetry_loop_started"})
        except Exception as e:
            logger.warning({"event": "telemetry_loop_error", "error": str(e)})


# --- Module-level helper for MQTT discovery publishing ---
def publish_discovery_if_available(client, controller, base_topic, qos, retain):
    """
    Publish MQTT discovery if the controller supports it.

    No-op if the controller has its own discovery publisher.

    Parameters
    ----------
    client : object
        MQTT client instance.
    controller : object
        Controller instance (may have publish_discovery method).
    base_topic : str
        MQTT base topic.
    qos : int
        MQTT QoS level.
    retain : bool
        MQTT retain flag.
    """
    try:
        if hasattr(controller, "publish_discovery"):
            controller.publish_discovery(client, base_topic, qos=qos, retain=retain)
    except Exception as e:
        logger.error({"event": "discovery_publish_error", "error": repr(e)})

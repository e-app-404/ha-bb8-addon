# addon/bb8_core/echo_startup.py
import logging
import os


_log = logging.getLogger("bb8.echo_boot")


def start_echo_if_required(cfg):
    """Start echo responder via threading when env requires it."""
    require_echo = os.getenv("REQUIRE_DEVICE_ECHO", "0") == "1"
    
    # Check config for echo enable option
    if isinstance(cfg, dict):
        opt_enable = bool(cfg.get("enable_echo", False))
    else:
        opt_enable = bool(getattr(cfg, "enable_echo", False))
    
    if require_echo or opt_enable:
        _log.info(
            "Echo responder: ENABLED (require_echo=%s opt_enable=%s)",
            require_echo, opt_enable
        )
        # Force-enable echo via environment variable override
        os.environ["ENABLE_ECHO_RAW"] = "true"
        _log.info("Environment override: ENABLE_ECHO_RAW=true")
        
        # Don't start a thread here - let run.sh supervisor handle it
        # The supervisor checks ENABLE_ECHO_RAW and spawns echo_responder
        _log.info("Echo startup delegated to supervisor loop")
    else:
        _log.info(
            "Echo responder: DISABLED (require_echo=%s opt_enable=%s)",
            require_echo, opt_enable
        )
import json
import logging
import os
import pathlib
import re
import sys
import tempfile

# Use shared config
try:
    from .addon_config import load_config

    _cfg, _src = load_config()
except Exception:
    _cfg, _src = {}, {}


# Expanded redaction pattern
REDACT = re.compile(
    r"(?i)\b(pass(word)?|token|apikey|api_key|secret|bearer)\b\s*[:=]\s*([^\s,]+)"
)


def redact(s: str) -> str:
    return REDACT.sub(lambda m: f"{m.group(1)}=***REDACTED***", s)


class JsonRedactingHandler(logging.StreamHandler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = record.msg
            if isinstance(msg, dict):
                line = json.dumps(msg, default=str)
            else:
                line = str(msg)
            # Use new redact function
            line = redact(line)
            stream = self.stream if hasattr(self, "stream") else sys.stdout
            stream.write(line + "\n")
        except Exception:
            super().emit(record)


# Structured loggers for evidence-friendly logs
LOG_LEVEL = _cfg.get("LOG_LEVEL") or os.environ.get("BB8_LOG_LEVEL", "DEBUG")
logger = logging.getLogger("bb8_addon")
bridge_logger = logging.getLogger("bb8.bridge")
ble_logger = logging.getLogger("bb8.ble")

# Attach redacting handler to all loggers
handler = JsonRedactingHandler()
handler.setLevel(LOG_LEVEL)
for log in (logger, bridge_logger, ble_logger):
    log.setLevel(LOG_LEVEL)
    log.handlers.clear()
    log.addHandler(handler)
    log.propagate = False


# Structured event emitters
def log_command_received(command: str, topic: str, payload: dict):
    bridge_logger.info(
        {
            "event": "command_received",
            "topic": topic,
            "command": command,
            "payload": {
                k: v for k, v in payload.items() if k != "password" and k != "token"
            },
        }
    )


def log_device_handler_invoked(handler: str, args: dict):
    bridge_logger.info(
        {
            "event": "device_handler_invoked",
            "handler": handler,
            "args": {k: v for k, v in args.items() if k != "password" and k != "token"},
        }
    )


def log_ble_link_started(mac: str):
    ble_logger.info({"event": "ble_link_started", "mac": mac})


def log_echo_published(topic: str, payload: dict):
    bridge_logger.info(
        {
            "event": "echo_published",
            "topic": topic,
            "payload": {
                k: v for k, v in payload.items() if k != "password" and k != "token"
            },
        }
    )


def _writable(path: str) -> bool:
    try:
        p = pathlib.Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "a"):
            pass
        return True
    except Exception:
        return False


def init_file_handler(
    default_path="/addons/local/beep_boop_bb8/reports/ha_bb8_addon.log",
) -> logging.Handler:
    """
    Prefer LOG_PATH from config, then BB8_LOG_PATH env, then default_path, then /tmp, then stderr.
    Emits one warning on fallback.
    """
    candidate = _cfg.get("LOG_PATH") or os.environ.get("BB8_LOG_PATH") or default_path
    # Detect environment: if running in Home Assistant, /addons is present and /Volumes is not
    is_ha = os.path.exists("/addons") and not os.path.exists("/Volumes")
    # If running in HA and candidate starts with /Volumes, strip it
    if is_ha and candidate.startswith("/Volumes"):
        candidate = candidate.replace("/Volumes", "", 1)
    # If running locally and candidate starts with /addons, prepend /Volumes
    if not is_ha and candidate.startswith("/addons"):
        candidate = "/Volumes" + candidate
    print(f"[LOGGING DEBUG] Resolved LOG_PATH candidate: {candidate}")
    print(f"[LOGGING DEBUG] Writable: {_writable(candidate)}")
    if not _writable(candidate):
        tmp = os.path.join(tempfile.gettempdir(), "bb8_addon.log")
        print(
            f"[LOGGING DEBUG] Fallback to temp log path: {tmp}, Writable: {_writable(tmp)}"
        )
        candidate = tmp if _writable(tmp) else None
        logger.warning({"event": "log_path_fallback", "target": candidate or "stderr"})
    if candidate:
        return logging.FileHandler(candidate)
    return logging.StreamHandler()


LOG_LEVEL = os.environ.get("BB8_LOG_LEVEL", "DEBUG")
logger.setLevel(LOG_LEVEL)
formatter = logging.Formatter("%(asctime)s %(levelname)s:%(name)s: %(message)s")

try:
    fh = init_file_handler()
    fh.setLevel(LOG_LEVEL)
    fh.setFormatter(formatter)
    logger.addHandler(fh)
except Exception as e:
    print(f"Failed to open log file: {e}", file=sys.stderr)

ch = logging.StreamHandler(sys.stdout)
ch.setLevel(LOG_LEVEL)
ch.setFormatter(formatter)
logger.addHandler(ch)

logger.setLevel(logging.INFO)
if not logger.handlers:
    h = logging.StreamHandler()
    fmt = logging.Formatter("%(asctime)s %(levelname)s:%(name)s:%(message)s")
    h.setFormatter(fmt)
    logger.addHandler(h)
    logger.propagate = False

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
    r"(?i)[\"']?\b(pass(word)?|token|apikey|api_key|secret|bearer)\b[\"']?\s*[:=]\s*[\"']?([^\"',\s]+)[\"']?"
)


def redact(s: str) -> str:
    return REDACT.sub(lambda m: f"{m.group(1)}=***REDACTED***", s)


class JsonRedactingHandler(logging.StreamHandler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = record.msg
            line = json.dumps(msg, default=str) if isinstance(msg, dict) else str(msg)
            line = redact(line)
            stream = self.stream if hasattr(self, "stream") else sys.stdout
            stream.write(line + "\n")
        except Exception:
            super().emit(record)


# Structured loggers for evidence-friendly logs
LOG_LEVEL = _cfg.get("LOG_LEVEL") or os.environ.get("BB8_LOG_LEVEL", "DEBUG")
# Use module qualified logger names so tests that import logger expect the
# module path to match.
logger = logging.getLogger(__name__)
bridge_logger = logging.getLogger(f"{__name__}.bridge")
import atexit

ble_logger = logging.getLogger(f"{__name__}.ble")

# Back-compat mapping expected by some tests
LOG_LEVEL_MAP = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}

# Attach redacting handler to all loggers, deduplicate handlers
handler = JsonRedactingHandler()
handler.setLevel(LOG_LEVEL)
for log in (logger, bridge_logger, ble_logger):
    log.setLevel(LOG_LEVEL)
    log.handlers.clear()  # Deduplicate handlers on restart
    log.addHandler(handler)
    log.propagate = False


# Ensure all log handlers are flushed on exit
def _flush_all_log_handlers():
    """Flush all log handlers safely, handling already-closed streams."""
    # Allow tests to patch logging.getLogger() and return a mock root logger.
    # Consult the root logger first (as tests do), then fall back to module
    # loggers to ensure real runtime behaviour is preserved.
    seen = set()
    try:
        root = logging.getLogger()
    except Exception:
        root = None

    candidates = [root, logger, bridge_logger, ble_logger]
    for log in candidates:
        if log is None:
            continue
        lid = id(log)
        if lid in seen:
            continue
        seen.add(lid)
        for h in getattr(log, "handlers", []):
            if hasattr(h, "flush"):
                try:
                    # Only treat the stream as closed when the 'closed' attribute
                    # is a real boolean. Some tests use MagicMock handlers where
                    # h.stream.closed is itself a MagicMock, which is truthy but
                    # not a reliable indicator of closed state.
                    stream_closed = False
                    if hasattr(h, "stream") and hasattr(h.stream, "closed"):
                        closed_attr = h.stream.closed
                        if isinstance(closed_attr, bool) and closed_attr:
                            stream_closed = True
                    if stream_closed:
                        continue
                    h.flush()
                except Exception:
                    # Silently ignore any error raised by flush; tests expect
                    # _flush_all_log_handlers to swallow handler-level exceptions.
                    pass


atexit.register(_flush_all_log_handlers)


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
    default_path="/addons/docs/reports/ha_bb8_addon.log",
) -> logging.Handler:
    """
    Pref config LOG_PATH, then BB8_LOG_PATH env, then default_path, then /tmp,
    then stderr. Emits one warning on fallback.
    """
    candidate = _cfg.get("LOG_PATH") or os.environ.get("BB8_LOG_PATH") or default_path
    # Detect env: if running in HA, /addons is present and /Volumes is not
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
            f"[LOGGING DEBUG] Fallback to temp log path: {tmp}, "
            f"Writable: {_writable(tmp)}"
        )
        candidate = tmp if _writable(tmp) else None
        logger.warning(
            {
                "event": "log_path_fallback",
                "target": candidate or "stderr",
            }
        )
        # Log explicit fallback
        print(
            f"[LOGGING WARNING] Log file not writable, using fallback: "
            f"{candidate or 'stderr'}"
        )
    if candidate:
        return logging.FileHandler(candidate)
    print("[LOGGING WARNING] No writable log file, using StreamHandler (stderr)")
    return logging.StreamHandler()


def _get_log_level(override: str | None = None) -> int:
    """Resolve log level from environment or config and return numeric level.

    The function checks, in order: LOG_LEVEL, LOGGING_LEVEL, BB8_LOG_LEVEL
    and falls back to logging.INFO for invalid or missing values.
    """
    # If override provided, use it first
    if override:
        lvl_name = str(override).upper()
        return LOG_LEVEL_MAP.get(lvl_name, logging.INFO)

    # Prefer explicit env vars, then fallback to BB8_LOG_LEVEL
    lvl = os.environ.get("LOG_LEVEL") or os.environ.get("LOGGING_LEVEL")
    if not lvl:
        lvl = os.environ.get("BB8_LOG_LEVEL")
    if not lvl:
        return logging.INFO
    # Normalise and map
    lvl_name = str(lvl).upper()
    return LOG_LEVEL_MAP.get(lvl_name, logging.INFO)


# Public alias expected by some tests
def get_log_level(override: str | None = None) -> int:
    return _get_log_level(override=override)


def setup_logging(level: str | None = None):
    """Convenience wrapper to (re)initialize logging handlers as tests expect.

    Optional `level` argument can be provided (string) to override env/config.
    """
    # Re-evaluate level and reconfigure handlers
    numeric_level = (
        get_log_level(level)
        if isinstance(level, str)
        else (_get_log_level() if level is None else level)
    )
    for log in (logger, bridge_logger, ble_logger):
        log.setLevel(numeric_level)
        # Ensure at least one handler exists
        if not log.handlers:
            log.addHandler(JsonRedactingHandler())


__all__ = [
    "LOG_LEVEL_MAP",
    "_flush_all_log_handlers",
    "_get_log_level",
    "get_log_level",
    "logger",
    "setup_logging",
]


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

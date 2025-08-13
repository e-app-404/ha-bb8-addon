import json
import logging
import os
import re
import sys
import pathlib
import tempfile


# Expanded redaction pattern
REDACT = re.compile(r'(?i)\b(pass(word)?|token|apikey|api_key|secret|bearer)\b\s*[:=]\s*([^\s,]+)')
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


logger = logging.getLogger("bb8_addon")

def _writable(path: str) -> bool:
    try:
        p = pathlib.Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "a"):
            pass
        return True
    except Exception:
        return False

def init_file_handler(default_path="/config/hestia/diagnostics/reports/bb8_addon_logs.log") -> logging.Handler:
    """
    Prefer BB8_LOG_PATH env, fall back to default_path, then /tmp, then stderr.
    Emits one warning on fallback.
    """
    candidate = os.environ.get("BB8_LOG_PATH", default_path)
    if not _writable(candidate):
        tmp = os.path.join(tempfile.gettempdir(), "bb8_addon.log")
        candidate = tmp if _writable(tmp) else None
        logger.warning({"event": "log_path_fallback", "target": candidate or "stderr"})
    if candidate:
        return logging.FileHandler(candidate)
    return logging.StreamHandler()

LOG_LEVEL = os.environ.get("BB8_LOG_LEVEL", "DEBUG")
logger.setLevel(LOG_LEVEL)
formatter = logging.Formatter('%(asctime)s %(levelname)s:%(name)s: %(message)s')

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

import json
import logging
import os
import re
import sys


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

# Set log path to new location
LOG_PATH = os.environ.get("BB8_LOG_PATH", "/config/hestia/diagnostics/reports/bb8_addon_logs.log")
LOG_LEVEL = os.environ.get("BB8_LOG_LEVEL", "DEBUG")

logger = logging.getLogger("bb8_addon")
logger.setLevel(LOG_LEVEL)
formatter = logging.Formatter('%(asctime)s %(levelname)s:%(name)s: %(message)s')

try:
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    fh = logging.FileHandler(LOG_PATH)
    fh.setLevel(LOG_LEVEL)
    fh.setFormatter(formatter)
    logger.addHandler(fh)
except Exception as e:
    print(f"Failed to open log file {LOG_PATH}: {e}", file=sys.stderr)

ch = logging.StreamHandler(sys.stdout)
ch.setLevel(LOG_LEVEL)
ch.setFormatter(formatter)
logger.addHandler(ch)

logger.setLevel(logging.INFO)
if not logger.handlers:
    logger.addHandler(JsonRedactingHandler())

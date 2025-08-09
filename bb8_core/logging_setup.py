import logging
import os
import sys

LOG_PATH = os.environ.get("BB8_LOG_PATH", "/app/meta/bb8_addon_logs.log")
LOG_LEVEL = os.environ.get("BB8_LOG_LEVEL", "DEBUG")

logger = logging.getLogger("bb8_addon")
logger.setLevel(LOG_LEVEL)
formatter = logging.Formatter('%(asctime)s %(levelname)s:%(name)s: %(message)s')

# File handler
try:
    fh = logging.FileHandler(LOG_PATH)
    fh.setLevel(LOG_LEVEL)
    fh.setFormatter(formatter)
    logger.addHandler(fh)
except Exception as e:
    print(f"Failed to open log file {LOG_PATH}: {e}", file=sys.stderr)

# Console handler (always)
ch = logging.StreamHandler(sys.stdout)
ch.setLevel(LOG_LEVEL)
ch.setFormatter(formatter)
logger.addHandler(ch)

import os
import json
import logging
from datetime import datetime, timezone
from typing import Any

# ----------------------------
# Log directory
# ----------------------------
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

LOG_FILE = os.path.join(LOG_DIR, "onboarding.log")

# ----------------------------
# Logger configuration
# ----------------------------
logger = logging.getLogger("onboarding_agent")
logger.setLevel(logging.INFO)

formatter = logging.Formatter(
    "%(asctime)s | %(levelname)s | %(message)s"
)

# Console handler (stdout)
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)

# File handler (persistent audit log)
file_handler = logging.FileHandler(LOG_FILE)
file_handler.setFormatter(formatter)

# Avoid duplicate handlers on reload
if not logger.handlers:
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
else:
    logger.handlers = [console_handler, file_handler]


# ----------------------------
# Helpers
# ----------------------------
def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def log_event(event: str, **fields: Any) -> None:
    """
    Write a structured JSON log entry.
    """
    payload = {
        "ts": now_iso(),
        "event": event,
        **fields,
    }
    logger.info(json.dumps(payload, default=str))

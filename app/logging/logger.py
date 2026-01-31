"""
Structured logging for the onboarding agent.
Provides audit trail and observability.
"""

import os
import json
import logging
from datetime import datetime, timezone
from typing import Any

# ----------------------------
# Log directory setup
# ----------------------------
LOG_DIR = os.getenv("LOG_DIR", "logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "onboarding.log")

# ----------------------------
# Logger configuration
# ----------------------------
logger = logging.getLogger("onboarding_agent")
logger.setLevel(logging.INFO)

# Formatter
formatter = logging.Formatter(
    "%(asctime)s | %(levelname)s | %(message)s"
)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
console_handler.setLevel(logging.INFO)

# File handler
file_handler = logging.FileHandler(LOG_FILE)
file_handler.setFormatter(formatter)
file_handler.setLevel(logging.INFO)

# Avoid duplicate handlers on reload
if not logger.handlers:
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)


def now_iso() -> str:
    """Return current UTC timestamp in ISO format."""
    return datetime.now(timezone.utc).isoformat()


def log_event(event: str, **fields: Any) -> None:
    """
    Write a structured JSON log entry.
    
    Args:
        event: Event name (e.g., "webhook.received", "decision.made")
        **fields: Additional fields to include in the log
    """
    payload = {
        "ts": now_iso(),
        "event": event,
        **fields,
    }
    logger.info(json.dumps(payload, default=str))


def log_error(event: str, error: Exception, **fields: Any) -> None:
    """Log an error event."""
    payload = {
        "ts": now_iso(),
        "event": event,
        "error": str(error),
        "error_type": type(error).__name__,
        **fields,
    }
    logger.error(json.dumps(payload, default=str))


def log_state_transition(
    from_stage: str,
    to_stage: str,
    account_id: str,
    correlation_id: str,
    **fields: Any
) -> None:
    """Log a state machine transition."""
    log_event(
        "state.transition",
        from_stage=from_stage,
        to_stage=to_stage,
        account_id=account_id,
        correlation_id=correlation_id,
        **fields,
    )

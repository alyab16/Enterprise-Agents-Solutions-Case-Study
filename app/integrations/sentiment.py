"""
Customer Sentiment Analysis integration.

Analyses customer interactions (emails, chat messages, support tickets)
to produce sentiment scores, trends, and early-warning signals. Feeds
into the health assessment so CS can act before tasks actually stall.

Uses a HuggingFace DistilBERT transformer model (distilbert-base-uncased-
finetuned-sst-2-english) for real ML inference when torch + transformers
are installed.  Falls back to keyword-based scoring otherwise.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Transformer-based sentiment model (lazy-loaded singleton)
# ---------------------------------------------------------------------------

_pipeline = None  # Will hold the HF pipeline once loaded
_USE_TRANSFORMER: bool | None = None  # None = not yet checked


def _load_model():
    """Lazy-load the HuggingFace sentiment pipeline on first use."""
    global _pipeline, _USE_TRANSFORMER
    if _USE_TRANSFORMER is not None:
        return  # already attempted

    try:
        from transformers import pipeline as hf_pipeline
        _pipeline = hf_pipeline(
            "sentiment-analysis",
            model="distilbert-base-uncased-finetuned-sst-2-english",
            top_k=None,          # return scores for all labels
            truncation=True,     # handle long texts gracefully
        )
        _USE_TRANSFORMER = True
        logger.info("Sentiment model loaded: distilbert-base-uncased-finetuned-sst-2-english")
    except Exception as exc:
        _USE_TRANSFORMER = False
        logger.warning("Transformer model unavailable, falling back to keyword scorer: %s", exc)


# ---------------------------------------------------------------------------
# Mock interaction store: account_id -> list of interactions
# ---------------------------------------------------------------------------

_INTERACTIONS: Dict[str, List[dict]] = {}


# Seed data aligned with simulation profiles so demo has realistic signals.
_SEED_INTERACTIONS: Dict[str, List[dict]] = {
    # no_login profile — customer is frustrated they can't access the platform
    "STARTER-007": [
        {
            "id": "INT-S007-1",
            "channel": "email",
            "direction": "inbound",
            "author": "customer",
            "text": "We signed up five days ago and still can't log in. This is very frustrating.",
            "timestamp_offset_days": -4,
        },
        {
            "id": "INT-S007-2",
            "channel": "email",
            "direction": "inbound",
            "author": "customer",
            "text": "Following up again — no one has responded to my previous email about login issues.",
            "timestamp_offset_days": -2,
        },
        {
            "id": "INT-S007-3",
            "channel": "email",
            "direction": "outbound",
            "author": "cs_team",
            "text": "Apologies for the delay. Your credentials were sent to the email on file. Please check spam.",
            "timestamp_offset_days": -1,
        },
    ],
    # stalled profile — customer disengaged and unhappy with slow progress
    "GROWTH-008": [
        {
            "id": "INT-G008-1",
            "channel": "email",
            "direction": "inbound",
            "author": "customer",
            "text": "It has been over a week and the kickoff call still hasn't been scheduled. We expected this to move faster.",
            "timestamp_offset_days": -8,
        },
        {
            "id": "INT-G008-2",
            "channel": "support_ticket",
            "direction": "inbound",
            "author": "customer",
            "text": "Ticket: Onboarding stalled, no progress, considering alternatives. Very disappointed.",
            "timestamp_offset_days": -5,
        },
        {
            "id": "INT-G008-3",
            "channel": "email",
            "direction": "inbound",
            "author": "customer",
            "text": "We are losing confidence in this product. Our leadership is asking why we haven't launched yet.",
            "timestamp_offset_days": -2,
        },
    ],
    # blocked_sso profile — mixed, frustrated about SSO delays specifically
    "ENTERPRISE-009": [
        {
            "id": "INT-E009-1",
            "channel": "email",
            "direction": "inbound",
            "author": "customer",
            "text": "The kickoff call went well, thank you. Looking forward to getting started.",
            "timestamp_offset_days": -7,
        },
        {
            "id": "INT-E009-2",
            "channel": "email",
            "direction": "inbound",
            "author": "customer",
            "text": "Our IT team has been waiting for SSO metadata instructions. Can you provide the IdP configuration guide?",
            "timestamp_offset_days": -4,
        },
        {
            "id": "INT-E009-3",
            "channel": "email",
            "direction": "inbound",
            "author": "customer",
            "text": "SSO is still blocked. This is delaying our entire rollout. We need this resolved urgently.",
            "timestamp_offset_days": -1,
        },
    ],
    # Happy path — positive engagement
    "ACME-001": [
        {
            "id": "INT-A001-1",
            "channel": "email",
            "direction": "inbound",
            "author": "customer",
            "text": "Thank you for the quick provisioning. The welcome email was clear and helpful.",
            "timestamp_offset_days": -3,
        },
        {
            "id": "INT-A001-2",
            "channel": "email",
            "direction": "inbound",
            "author": "customer",
            "text": "Logged in successfully. The platform looks great. Looking forward to the kickoff.",
            "timestamp_offset_days": -1,
        },
    ],
}


# ---------------------------------------------------------------------------
# Sentiment scoring — transformer model with keyword fallback
# ---------------------------------------------------------------------------

def _score_text(text: str) -> float:
    """Return a sentiment score between -1.0 (very negative) and 1.0 (very positive).

    Uses DistilBERT when available; otherwise falls back to keyword matching.
    """
    _load_model()
    if _USE_TRANSFORMER:
        return _score_text_transformer(text)
    return _score_text_keywords(text)


def _score_text_transformer(text: str) -> float:
    """Score text using the HuggingFace DistilBERT sentiment model.

    The model returns POSITIVE/NEGATIVE labels with confidence scores.
    We map these to a -1.0 … +1.0 scale:
        POSITIVE 0.95 → +0.95
        NEGATIVE 0.80 → -0.80
    """
    results = _pipeline(text)[0]  # list of {label, score} dicts
    label_scores = {r["label"]: r["score"] for r in results}
    pos = label_scores.get("POSITIVE", 0.0)
    neg = label_scores.get("NEGATIVE", 0.0)
    # Map to [-1, 1]: positive confidence pushes toward +1, negative toward -1
    score = pos - neg
    return round(score, 2)


# ---------------------------------------------------------------------------
# Keyword fallback (used when torch/transformers are not installed)
# ---------------------------------------------------------------------------

_POSITIVE_KEYWORDS = {
    "thank", "thanks", "great", "excellent", "helpful", "looking forward",
    "happy", "pleased", "impressed", "well done", "smooth", "clear",
    "appreciate", "love", "good", "perfect", "awesome", "wonderful",
    "successful", "successfully",
}

_NEGATIVE_KEYWORDS = {
    "frustrated", "frustrating", "disappointed", "disappointing", "angry",
    "unacceptable", "terrible", "horrible", "worst", "poor", "slow",
    "delay", "delayed", "stalled", "blocked", "waiting", "no response",
    "no progress", "losing confidence", "considering alternatives",
    "urgently", "escalate", "concerned", "issue", "problem", "failed",
    "unhappy", "upset", "annoyed",
}


def _score_text_keywords(text: str) -> float:
    """Fallback keyword-based scorer."""
    lower = text.lower()
    pos = sum(1 for kw in _POSITIVE_KEYWORDS if kw in lower)
    neg = sum(1 for kw in _NEGATIVE_KEYWORDS if kw in lower)
    total = pos + neg
    if total == 0:
        return 0.0
    return round((pos - neg) / total, 2)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def _ensure_seeded(account_id: str) -> None:
    """Lazily seed interactions for an account if seed data exists."""
    if account_id not in _INTERACTIONS and account_id in _SEED_INTERACTIONS:
        now = datetime.utcnow()
        _INTERACTIONS[account_id] = [
            {
                **interaction,
                "timestamp": (now + timedelta(days=interaction["timestamp_offset_days"])).isoformat(),
            }
            for interaction in _SEED_INTERACTIONS[account_id]
        ]


def add_interaction(
    account_id: str,
    channel: str,
    direction: str,
    author: str,
    text: str,
) -> dict:
    """Record a new customer interaction."""
    _ensure_seeded(account_id)
    interaction = {
        "id": f"INT-{account_id}-{len(_INTERACTIONS.get(account_id, [])) + 1}",
        "channel": channel,
        "direction": direction,
        "author": author,
        "text": text,
        "timestamp": datetime.utcnow().isoformat(),
    }
    _INTERACTIONS.setdefault(account_id, []).append(interaction)
    return interaction


def get_sentiment_score(account_id: str) -> dict:
    """
    Compute an aggregate sentiment score for an account.

    Returns:
        score: float -1.0 to 1.0
        label: "positive" / "neutral" / "negative"
        interaction_count: how many interactions were analysed
        recent_scores: per-interaction scores for the most recent 5
    """
    _ensure_seeded(account_id)
    interactions = _INTERACTIONS.get(account_id, [])

    # Only score inbound customer messages (not CS outbound)
    customer_msgs = [i for i in interactions if i.get("author") == "customer"]

    if not customer_msgs:
        return {
            "account_id": account_id,
            "score": 0.0,
            "label": "neutral",
            "interaction_count": 0,
            "recent_scores": [],
            "summary": "No customer interactions recorded.",
        }

    scores = [_score_text(m["text"]) for m in customer_msgs]
    avg = round(sum(scores) / len(scores), 2)

    if avg >= 0.3:
        label = "positive"
    elif avg <= -0.3:
        label = "negative"
    else:
        label = "neutral"

    recent = customer_msgs[-5:]
    recent_scores = [
        {
            "text_preview": m["text"][:80] + ("..." if len(m["text"]) > 80 else ""),
            "score": _score_text(m["text"]),
            "channel": m["channel"],
            "timestamp": m.get("timestamp", ""),
        }
        for m in recent
    ]

    _load_model()
    return {
        "account_id": account_id,
        "score": avg,
        "label": label,
        "interaction_count": len(customer_msgs),
        "recent_scores": recent_scores,
        "model": "distilbert-base-uncased-finetuned-sst-2-english" if _USE_TRANSFORMER else "keyword-fallback",
        "summary": _build_summary(account_id, avg, label, customer_msgs),
    }


def get_sentiment_trend(account_id: str) -> dict:
    """
    Compute whether sentiment is improving, declining, or stable.

    Compares the average score of the older half vs. the newer half
    of customer interactions.
    """
    _ensure_seeded(account_id)
    interactions = _INTERACTIONS.get(account_id, [])
    customer_msgs = [i for i in interactions if i.get("author") == "customer"]

    if len(customer_msgs) < 2:
        return {
            "account_id": account_id,
            "trend": "insufficient_data",
            "detail": "Need at least 2 customer interactions to compute trend.",
        }

    mid = len(customer_msgs) // 2
    older = customer_msgs[:mid]
    newer = customer_msgs[mid:]

    older_avg = sum(_score_text(m["text"]) for m in older) / len(older)
    newer_avg = sum(_score_text(m["text"]) for m in newer) / len(newer)
    delta = round(newer_avg - older_avg, 2)

    if delta > 0.15:
        trend = "improving"
    elif delta < -0.15:
        trend = "declining"
    else:
        trend = "stable"

    return {
        "account_id": account_id,
        "trend": trend,
        "older_avg": round(older_avg, 2),
        "newer_avg": round(newer_avg, 2),
        "delta": delta,
    }


def _build_summary(account_id: str, score: float, label: str, msgs: list) -> str:
    """Build a human-readable sentiment summary."""
    count = len(msgs)
    if label == "positive":
        return (
            f"{account_id} sentiment is positive (score {score}) across "
            f"{count} interaction(s). Customer is engaged and satisfied."
        )
    elif label == "negative":
        return (
            f"{account_id} sentiment is negative (score {score}) across "
            f"{count} interaction(s). Customer is expressing frustration — "
            f"proactive outreach recommended."
        )
    return (
        f"{account_id} sentiment is neutral (score {score}) across "
        f"{count} interaction(s)."
    )


def reset_all() -> None:
    """Clear all interaction data (for testing/reset)."""
    _INTERACTIONS.clear()

"""
Minimal state utility functions used by the invariant checkers.

These helpers mutate a dict-based state to add violations and warnings.
They are used by the business rule validators in app/agent/invariants/.
"""

from typing import Dict, Any


def add_violation(state: dict, domain: str, message: str) -> None:
    """Record a blocking invariant violation."""
    if state.get("violations") is None:
        state["violations"] = {}
    state["violations"].setdefault(domain, []).append(message)


def add_warning(state: dict, domain: str, message: str) -> None:
    """Record a non-blocking warning."""
    if state.get("warnings") is None:
        state["warnings"] = {}
    state["warnings"].setdefault(domain, []).append(message)

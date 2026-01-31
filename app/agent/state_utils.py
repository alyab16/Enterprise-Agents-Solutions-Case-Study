from typing import Optional
import uuid
from .state import AgentState


def init_state(
    *,
    account_id: Optional[str] = None,
    correlation_id: Optional[str] = None,
    event_type: Optional[str] = None,
) -> AgentState:
    """
    Initialize a clean AgentState for a new onboarding run.
    """
    return AgentState(
        account_id=account_id or "",
        correlation_id=correlation_id or str(uuid.uuid4()),
        event_type=event_type or "manual",
        account=None,
        opportunity=None,
        contract=None,
        user=None,
        invoice=None,
        provisioning=None,
        violations={},
        warnings={},
        decisions=[],
        overrides={},
        stage="initialized",
        decision="PENDING",
        risk_analysis={},
        actions_taken=[],
        notifications_sent=[],
        human_summary="",
        recommended_actions=[],
    )


def add_violation(state: AgentState, domain: str, message: str) -> None:
    """Record a blocking invariant violation."""
    if state.get("violations") is None:
        state["violations"] = {}
    state["violations"].setdefault(domain, []).append(message)


def add_warning(state: AgentState, domain: str, message: str) -> None:
    """Record a non-blocking warning."""
    if state.get("warnings") is None:
        state["warnings"] = {}
    state["warnings"].setdefault(domain, []).append(message)


def has_blockers(state: AgentState) -> bool:
    """Returns True if any domain has at least one violation."""
    violations = state.get("violations", {})
    return any(msgs for msgs in violations.values() if msgs)


def has_warnings(state: AgentState) -> bool:
    """Returns True if any domain has at least one warning."""
    warnings = state.get("warnings", {})
    return any(msgs for msgs in warnings.values() if msgs)


def record_decision(state: AgentState, decision: str) -> None:
    """Append a routing or business decision made by the agent."""
    if state.get("decisions") is None:
        state["decisions"] = []
    state["decisions"].append(decision)


def record_action(state: AgentState, action_type: str, details: dict) -> None:
    """Record an action taken by the agent."""
    if state.get("actions_taken") is None:
        state["actions_taken"] = []
    state["actions_taken"].append({
        "type": action_type,
        **details
    })


def record_notification(state: AgentState, channel: str, recipient: str, message: str) -> None:
    """Record a notification sent by the agent."""
    if state.get("notifications_sent") is None:
        state["notifications_sent"] = []
    state["notifications_sent"].append({
        "channel": channel,
        "recipient": recipient,
        "message": message
    })

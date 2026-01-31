"""
Router functions for conditional edges in the agent graph.
"""

from app.agent.state import AgentState


def after_decision(state: AgentState) -> str:
    """
    Route based on the decision made.
    
    Returns:
        - "send_notifications" for BLOCK or ESCALATE
        - "provision" for PROCEED
    """
    decision = state.get("decision", "BLOCK")
    
    if decision == "PROCEED":
        return "provision"
    else:
        # BLOCK or ESCALATE - send notifications
        return "send_notifications"


def after_notifications(state: AgentState) -> str:
    """
    Route after sending notifications.
    
    Always goes to generate_summary as the final step.
    """
    return "generate_summary"


def after_provision(state: AgentState) -> str:
    """
    Route after provisioning.
    
    Always goes to generate_summary.
    """
    return "generate_summary"

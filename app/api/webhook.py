"""
Webhook API endpoints for the onboarding agent.
"""

from fastapi import APIRouter, HTTPException
from app.models.events import TriggerEvent, OnboardingResponse, DebugPayload
from app.agent import run_onboarding
from app.agent.state_utils import init_state
from app.agent.invariants import (
    check_account_invariants,
    check_user_invariants,
    check_contract_invariants,
    check_opportunity_invariants,
    check_invoice_invariants,
)
from app.llm.risk_analyzer import analyze_risks
from app.logging.logger import log_event

router = APIRouter(tags=["webhooks"])


@router.post("/webhook/onboarding", response_model=OnboardingResponse)
async def onboarding_webhook(event: TriggerEvent):
    """
    Main webhook endpoint for triggering customer onboarding.
    
    This endpoint:
    1. Receives an event (e.g., from Salesforce when an Opportunity closes)
    2. Runs the full onboarding agent graph
    3. Returns the decision and all relevant details
    
    Example trigger events:
    - opportunity.closed_won: New deal closed
    - contract.executed: Contract signed
    - manual.trigger: Manual onboarding trigger
    """
    
    # Log the incoming event
    log_event(
        "webhook.received",
        account_id=event.account_id,
        correlation_id=event.correlation_id,
        event_type=event.event_type,
    )
    
    try:
        # Run the full onboarding graph
        final_state = run_onboarding(
            account_id=event.account_id,
            correlation_id=event.correlation_id,
            event_type=event.event_type,
        )
        
        # Build response
        risk_analysis = final_state.get("risk_analysis", {})
        
        response = OnboardingResponse(
            correlation_id=event.correlation_id,
            account_id=event.account_id,
            decision=final_state.get("decision", "UNKNOWN"),
            stage=final_state.get("stage", "unknown"),
            risk_level=risk_analysis.get("risk_level"),
            summary=risk_analysis.get("summary") or final_state.get("human_summary"),
            violations=final_state.get("violations", {}),
            warnings=final_state.get("warnings", {}),
            actions_taken=final_state.get("actions_taken", []),
            notifications_sent=final_state.get("notifications_sent", []),
            recommended_actions=final_state.get("recommended_actions", []),
            provisioning=final_state.get("provisioning"),
        )
        
        log_event(
            "webhook.response",
            account_id=event.account_id,
            correlation_id=event.correlation_id,
            decision=response.decision,
        )
        
        return response
        
    except Exception as e:
        log_event(
            "webhook.error",
            account_id=event.account_id,
            correlation_id=event.correlation_id,
            error=str(e),
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/debug/onboarding")
async def debug_onboarding(payload: DebugPayload):
    """
    Debug endpoint for testing with custom mock data.
    
    Allows you to pass in specific account/user/contract/opportunity data
    to test different scenarios without using the mock integrations.
    """
    
    # Initialize state
    state = init_state(event_type="debug")
    
    # Hydrate with provided mock data
    state["account"] = payload.account
    state["user"] = payload.user
    state["contract"] = payload.contract
    state["opportunity"] = payload.opportunity
    state["invoice"] = payload.invoice
    
    # Run invariant checks
    check_account_invariants(state)
    check_user_invariants(state)
    check_contract_invariants(state)
    check_opportunity_invariants(state)
    check_invoice_invariants(state)
    
    # Run risk analysis
    risk_analysis = analyze_risks(state)
    state["risk_analysis"] = risk_analysis
    
    # Make decision
    violations = state.get("violations", {})
    warnings = state.get("warnings", {})
    
    violation_count = sum(len(msgs) for msgs in violations.values())
    warning_count = sum(len(msgs) for msgs in warnings.values())
    
    if violation_count > 0:
        decision = "BLOCK"
    elif warning_count > 0:
        decision = "ESCALATE"
    else:
        decision = "PROCEED"
    
    return {
        "decision": decision,
        "violations": violations,
        "warnings": warnings,
        "risk_analysis": risk_analysis,
    }

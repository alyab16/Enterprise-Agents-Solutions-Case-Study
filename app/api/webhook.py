"""
Webhook API endpoints for the onboarding agent.

=============================================================================
WHAT IS THIS FILE?
=============================================================================

This file defines the REST API endpoints that EXTERNAL SYSTEMS call to trigger
the onboarding agent. Think of it as the "front door" to the agent.

TYPICAL FLOW:
-------------
1. Salesforce detects an Opportunity changed to "Closed Won"
2. Salesforce sends a webhook (HTTP POST) to /webhook/onboarding
3. This code receives the request, runs the agent, and returns the result
4. Salesforce (or the calling system) can then act on the result

EXAMPLE REQUEST:
----------------
POST /webhook/onboarding
{
    "account_id": "ACME-001",
    "event_type": "opportunity.closed_won",
    "correlation_id": "sf-12345"  // optional, for tracking
}

EXAMPLE RESPONSE:
-----------------
{
    "decision": "PROCEED",
    "account_id": "ACME-001",
    "correlation_id": "sf-12345",
    "summary": "ACME Corp is ready for onboarding...",
    "provisioning": {
        "tenant_id": "TEN-ABC123",
        "onboarding_tasks": {...}
    }
}
=============================================================================
"""

from fastapi import APIRouter, HTTPException
from typing import Optional

# Import our models (Pydantic classes that define request/response structure)
from app.models.events import TriggerEvent, OnboardingResponse, DebugPayload

# Import the main agent function - this is where the magic happens
from app.agent import run_onboarding

# Import helper functions
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

# Import report generator so we can create reports
from app.reports import generate_full_run_report

# Create the router - this groups related endpoints together
router = APIRouter(tags=["webhooks"])


# =============================================================================
# MAIN WEBHOOK ENDPOINT
# =============================================================================

@router.post("/webhook/onboarding", response_model=OnboardingResponse)
async def onboarding_webhook(
    event: TriggerEvent,
    generate_report: bool = True  # NEW: Generate reports by default
):
    """
    Main webhook endpoint for triggering customer onboarding.
    
    HOW IT WORKS:
    -------------
    1. Receives a TriggerEvent with account_id and event_type
    2. Calls run_onboarding() which executes the full LangGraph workflow:
       - Fetches data from Salesforce, CLM, NetSuite
       - Validates business rules (invariants)
       - Analyzes risks using LLM (or rule-based fallback)
       - Makes a decision: PROCEED, ESCALATE, or BLOCK
       - If PROCEED: provisions tenant and creates onboarding tasks
       - Sends notifications via Slack and email
    3. Optionally generates HTML/Markdown/JSON reports
    4. Returns the decision and all relevant details
    
    WHEN IS THIS CALLED?
    --------------------
    - Salesforce Flow/Trigger when Opportunity.StageName = "Closed Won"
    - Manual API call from CS team
    - Scheduled batch job processing multiple accounts
    
    PARAMETERS:
    -----------
    - event: The trigger event containing account_id and metadata
    - generate_report: If True (default), creates report files in reports_output/
    
    RETURNS:
    --------
    OnboardingResponse with decision, violations, warnings, provisioning info, etc.
    """
    
    # -------------------------------------------------------------------------
    # STEP 1: Log that we received the webhook
    # -------------------------------------------------------------------------
    # This creates a structured log entry for observability/debugging
    log_event(
        "webhook.received",
        account_id=event.account_id,
        correlation_id=event.correlation_id,
        event_type=event.event_type,
    )
    
    try:
        # ---------------------------------------------------------------------
        # STEP 2: Run the full onboarding agent workflow
        # ---------------------------------------------------------------------
        # This is the core of the agent. It:
        # - Creates initial state with correlation_id for tracking
        # - Runs each node in the LangGraph: fetch → validate → analyze → decide
        # - Returns the final state with all data and decisions
        
        final_state = run_onboarding(
            account_id=event.account_id,
            correlation_id=event.correlation_id,
            event_type=event.event_type,
        )
        
        # ---------------------------------------------------------------------
        # STEP 3: Generate reports (if requested)
        # ---------------------------------------------------------------------
        # This creates files in reports_output/:
        # - run_report_ACME-001_20250201_123456.md (Markdown for humans)
        # - run_report_ACME-001_20250201_123456.html (HTML email template)
        # - audit_ACME-001_20250201_123456.json (JSON for systems/compliance)
        
        generated_reports = {}
        if generate_report:
            try:
                generated_reports = generate_full_run_report(final_state)
                log_event(
                    "webhook.reports_generated",
                    account_id=event.account_id,
                    files=list(generated_reports.keys()),
                )
            except Exception as report_error:
                # Don't fail the whole request if report generation fails
                log_event(
                    "webhook.report_generation_failed",
                    account_id=event.account_id,
                    error=str(report_error),
                )
        
        # ---------------------------------------------------------------------
        # STEP 4: Build the response object
        # ---------------------------------------------------------------------
        # We extract the relevant fields from final_state and package them
        # into a structured response that the calling system can use
        
        risk_analysis = final_state.get("risk_analysis", {})
        
        response = OnboardingResponse(
            # Identifiers for tracking
            correlation_id=event.correlation_id,
            account_id=event.account_id,
            
            # The main decision: PROCEED, ESCALATE, or BLOCK
            decision=final_state.get("decision", "UNKNOWN"),
            
            # Current stage (should be "complete" if everything worked)
            stage=final_state.get("stage", "unknown"),
            
            # Risk assessment from LLM or rule-based analysis
            risk_level=risk_analysis.get("risk_level"),
            summary=risk_analysis.get("summary") or final_state.get("human_summary"),
            
            # What issues were found?
            violations=final_state.get("violations", {}),  # Blocking issues
            warnings=final_state.get("warnings", {}),      # Non-blocking concerns
            
            # What did the agent do?
            actions_taken=final_state.get("actions_taken", []),
            notifications_sent=final_state.get("notifications_sent", []),
            
            # What should humans do next?
            recommended_actions=risk_analysis.get("recommended_actions", []),
            
            # If PROCEED, what was provisioned?
            provisioning=final_state.get("provisioning"),
            
            # NEW: Include report file paths
            generated_reports=generated_reports if generated_reports else None,
        )
        
        # ---------------------------------------------------------------------
        # STEP 5: Log the response and return
        # ---------------------------------------------------------------------
        log_event(
            "webhook.response",
            account_id=event.account_id,
            correlation_id=event.correlation_id,
            decision=response.decision,
            reports_generated=bool(generated_reports),
        )
        
        return response
        
    except Exception as e:
        # ---------------------------------------------------------------------
        # ERROR HANDLING
        # ---------------------------------------------------------------------
        # If anything goes wrong, log it and return a 500 error
        # In production, you might want to:
        # - Send an alert to the on-call team
        # - Retry the operation
        # - Queue for manual review
        
        log_event(
            "webhook.error",
            account_id=event.account_id,
            correlation_id=event.correlation_id,
            error=str(e),
        )
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# DEBUG ENDPOINT
# =============================================================================

@router.post("/debug/onboarding")
async def debug_onboarding(payload: DebugPayload):
    """
    Debug endpoint for testing with custom mock data.
    
    WHAT IS THIS FOR?
    -----------------
    This endpoint lets you test the validation and risk analysis logic
    WITHOUT calling the real integration mocks. You provide the exact
    data you want to test, and it runs the checks on that data.
    
    USE CASES:
    ----------
    - Testing edge cases that aren't in the mock data
    - Debugging specific validation rules
    - Unit testing the invariant checks
    
    EXAMPLE REQUEST:
    ----------------
    POST /debug/onboarding
    {
        "account": {"Name": "Test Corp", "IsDeleted": true},
        "opportunity": {"StageName": "Closed Won", "Amount": 50000}
    }
    
    EXAMPLE RESPONSE:
    -----------------
    {
        "decision": "BLOCK",
        "violations": {"account": ["Account is marked as deleted"]},
        "warnings": {},
        "risk_analysis": {...}
    }
    """
    
    # Initialize empty state
    state = init_state(event_type="debug")
    
    # Hydrate with provided mock data
    # (These would normally come from Salesforce/CLM/NetSuite API calls)
    state["account"] = payload.account
    state["user"] = payload.user
    state["clm"] = payload.contract  # Note: renamed from "contract" to "clm" internally
    state["opportunity"] = payload.opportunity
    state["invoice"] = payload.invoice
    
    # Run each invariant check
    # These functions look at the data and add violations/warnings to state
    check_account_invariants(state)
    check_user_invariants(state)
    check_contract_invariants(state)
    check_opportunity_invariants(state)
    check_invoice_invariants(state)
    
    # Run risk analysis (LLM or rule-based)
    risk_analysis = analyze_risks(state)
    state["risk_analysis"] = risk_analysis
    
    # Make decision based on violations and warnings
    violations = state.get("violations", {})
    warnings = state.get("warnings", {})
    
    violation_count = sum(len(msgs) for msgs in violations.values())
    warning_count = sum(len(msgs) for msgs in warnings.values())
    
    # Decision priority: violations → warnings → proceed
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

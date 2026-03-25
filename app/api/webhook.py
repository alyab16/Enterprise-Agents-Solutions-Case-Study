"""
Webhook API endpoints for the onboarding agent.

TYPICAL FLOW:
1. Salesforce detects an Opportunity changed to "Closed Won"
2. Salesforce sends a webhook (HTTP POST) to /webhook/onboarding
3. The Pydantic AI agent processes the request using native tool calling
4. Returns the decision and all relevant details
"""

from fastapi import APIRouter, HTTPException

from app.models.events import TriggerEvent, OnboardingResponse, DebugPayload
from app.agent import run_onboarding_async
from app.logging.logger import log_event
from app.reports import generate_full_run_report

router = APIRouter(tags=["webhooks"])


@router.post("/webhook/onboarding", response_model=OnboardingResponse)
async def onboarding_webhook(
    event: TriggerEvent,
    generate_report: bool = True,
):
    """
    Main webhook endpoint for triggering customer onboarding.

    The Pydantic AI agent autonomously:
    - Fetches data from Salesforce, CLM, NetSuite via tool calls
    - Validates business rules
    - Makes a decision: PROCEED, ESCALATE, or BLOCK
    - Sends notifications and/or provisions the account
    """
    log_event(
        "webhook.received",
        account_id=event.account_id,
        correlation_id=event.correlation_id,
        event_type=event.event_type,
    )

    try:
        final_state = await run_onboarding_async(
            account_id=event.account_id,
            correlation_id=event.correlation_id,
            event_type=event.event_type,
        )

        # Generate reports
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
                log_event(
                    "webhook.report_generation_failed",
                    account_id=event.account_id,
                    error=str(report_error),
                )

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
            recommended_actions=risk_analysis.get("recommended_actions", []),
            provisioning=final_state.get("provisioning"),
            generated_reports=generated_reports if generated_reports else None,
        )

        log_event(
            "webhook.response",
            account_id=event.account_id,
            correlation_id=event.correlation_id,
            decision=response.decision,
            reports_generated=bool(generated_reports),
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

    Runs validation and risk analysis on provided data without
    calling the real integration mocks.
    """
    from app.agent.invariants import (
        check_account_invariants,
        check_user_invariants,
        check_contract_invariants,
        check_opportunity_invariants,
        check_invoice_invariants,
    )
    from app.llm.risk_analyzer import _rule_based_analyze

    state = {
        "account": payload.account,
        "user": payload.user,
        "clm": payload.contract,
        "opportunity": payload.opportunity,
        "invoice": payload.invoice,
        "violations": {},
        "warnings": {},
        "api_errors": [],
    }

    check_account_invariants(state)
    check_user_invariants(state)
    check_contract_invariants(state)
    check_opportunity_invariants(state)
    check_invoice_invariants(state)

    risk_analysis = _rule_based_analyze(state)
    state["risk_analysis"] = risk_analysis

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

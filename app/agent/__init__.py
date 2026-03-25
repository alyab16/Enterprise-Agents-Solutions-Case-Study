"""
Enterprise Onboarding Agent — Pydantic AI + FastMCP architecture.

The agent uses native LLM tool calling to reason through the onboarding
workflow. No hardcoded graph or state machine — the LLM decides what
tools to call based on its observations.
"""

import asyncio
import uuid
from typing import Optional, Dict, Any

from app.agent.onboarding_agent import onboarding_agent
from app.agent.dependencies import OnboardingDeps
from app.agent.models import OnboardingResult
from app.logging.logger import log_event


async def run_onboarding_async(
    account_id: str,
    correlation_id: Optional[str] = None,
    event_type: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Run the onboarding workflow for an account using the Pydantic AI agent.

    The agent autonomously:
    1. Fetches data from Salesforce, CLM, and NetSuite
    2. Validates business rules
    3. Makes a routing decision (PROCEED / ESCALATE / BLOCK)
    4. Sends notifications and/or provisions the account

    Args:
        account_id: The account to onboard
        correlation_id: Optional tracking ID (generated if not provided)
        event_type: What triggered this run (webhook, demo, manual)

    Returns:
        Dict with decision, violations, warnings, provisioning, etc.
        Compatible with the existing OnboardingResponse model.
    """
    cid = correlation_id or str(uuid.uuid4())

    log_event(
        "agent.run.start",
        account_id=account_id,
        correlation_id=cid,
        event_type=event_type or "manual",
    )

    deps = OnboardingDeps(
        account_id=account_id,
        correlation_id=cid,
        event_type=event_type or "manual",
    )

    result = await onboarding_agent.run(
        f"Process customer onboarding for account ID: {account_id}",
        deps=deps,
    )

    output: OnboardingResult = result.output

    log_event(
        "agent.run.complete",
        account_id=account_id,
        correlation_id=cid,
        decision=output.decision,
        risk_level=output.risk_level,
    )

    # Build state-compatible dict for report generation and API response
    state = _result_to_state(output, account_id, cid, event_type)
    return state


def run_onboarding(
    account_id: str,
    correlation_id: Optional[str] = None,
    event_type: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Synchronous wrapper for run_onboarding_async.

    Maintains backward compatibility with existing API endpoints
    that call run_onboarding() synchronously.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        # We're inside an existing event loop (e.g. FastAPI)
        # Create a new task — the caller should await this
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            return pool.submit(
                asyncio.run,
                run_onboarding_async(account_id, correlation_id, event_type),
            ).result()
    else:
        return asyncio.run(
            run_onboarding_async(account_id, correlation_id, event_type)
        )


def _result_to_state(
    output: OnboardingResult,
    account_id: str,
    correlation_id: str,
    event_type: Optional[str],
) -> Dict[str, Any]:
    """
    Convert OnboardingResult to a state dict compatible with
    the report generator and API response models.
    """
    return {
        "account_id": account_id,
        "correlation_id": correlation_id,
        "event_type": event_type or "manual",
        "stage": "complete",
        "decision": output.decision,
        "risk_analysis": {
            "summary": output.summary,
            "risk_level": output.risk_level,
            "recommended_actions": [
                a.model_dump() for a in output.recommended_actions
            ],
            "can_proceed_with_warnings": output.decision != "BLOCK",
        },
        "violations": output.violations,
        "warnings": output.warnings,
        "api_errors": output.api_errors,
        "actions_taken": output.actions_taken,
        "notifications_sent": output.notifications_sent,
        "provisioning": output.provisioning,
        "human_summary": output.summary,
        "recommended_actions": [
            a.action for a in output.recommended_actions
        ],
        # Raw domain data for report generation
        "account": output.account_data,
        "user": output.user_data,
        "opportunity": output.opportunity_data,
        "contract": output.contract_data,
        "clm": output.clm_data,
        "invoice": output.invoice_data,
    }


__all__ = [
    "run_onboarding",
    "run_onboarding_async",
    "OnboardingResult",
    "OnboardingDeps",
]

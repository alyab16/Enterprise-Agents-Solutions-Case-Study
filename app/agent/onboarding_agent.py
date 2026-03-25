"""
Pydantic AI Onboarding Agent — the core of the agentic architecture.

This agent replaces the LangGraph state machine with a reasoning agent
that uses native tool calling to gather data, validate business rules,
make decisions, and take actions. The LLM decides what to do based on
tool results — no hardcoded graph or routing logic.

Architecture:
- Tools are registered in-process via @agent.tool decorators
- Each tool wraps an existing integration module
- The agent reasons through: fetch → validate → decide → act
- Structured output (OnboardingResult) ensures reliable responses
- FastMCP server definitions in app/mcp/ mirror these tools for
  future extraction to standalone MCP services

Model selection:
- Uses OpenAI GPT-4o when OPENAI_API_KEY is set
- Falls back to Ollama local model when no API key is available
"""

import json
import os
from typing import Any, Dict

from pydantic_ai import Agent, RunContext

from app.agent.dependencies import OnboardingDeps
from app.agent.models import OnboardingResult
from app.logging.logger import log_event


# ---------------------------------------------------------------------------
# Model selection
# ---------------------------------------------------------------------------

def _select_model():
    """Select the LLM model based on available API keys."""
    if os.getenv("OPENAI_API_KEY"):
        return os.getenv("OPENAI_MODEL", "openai:gpt-4o")

    # Fallback to Ollama local model
    ollama_base = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
    ollama_model = os.getenv("OLLAMA_MODEL", "llama3.2")

    from pydantic_ai.models.openai import OpenAIModel
    from pydantic_ai.providers.openai import OpenAIProvider

    return OpenAIModel(
        model_name=ollama_model,
        provider=OpenAIProvider(
            base_url=ollama_base,
            api_key="ollama",  # Ollama doesn't need a real key
        ),
    )


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are an enterprise Customer Success onboarding agent. Your job is to
autonomously process customer onboarding by gathering data from multiple
systems, validating business rules, assessing risks, making a routing
decision, and executing the appropriate actions.

## YOUR WORKFLOW

You have tools to interact with Salesforce, CLM (Contract Lifecycle
Management), NetSuite (invoicing), a provisioning system, a notification
system, and a business rule validation engine. Use them as follows:

1. **GATHER DATA** — You MUST fetch data from ALL systems before validating:
   a) Call `fetch_salesforce_account` (no args needed — uses context)
   b) ALWAYS call `fetch_salesforce_user` with the OwnerId from the account
   c) Call `fetch_salesforce_opportunity` (no args needed)
   d) Call `fetch_salesforce_contract` (no args needed)
   e) Call `fetch_clm_contract` (no args needed)
   f) Call `fetch_netsuite_invoice` (no args needed)

   Steps b-f can be called in parallel after step a completes.

   NOTE: Most fetch tools automatically use the onboarding account ID from context.
   Only `fetch_salesforce_user` requires an explicit user_id argument.
   You MUST call ALL fetch tools before calling validate_business_rules.

   IMPORTANT: If any fetch returns a response with "status": "API_ERROR"
   or similar error status (AUTH_ERROR, SERVER_ERROR, etc.), record it
   as an API error. API errors are BLOCKING — they prevent onboarding.

2. **VALIDATE** — Once data is gathered, call `validate_business_rules`
   with NO arguments. It automatically uses the data collected by the
   fetch tools. Returns violations (blocking) and warnings (non-blocking).

3. **DECIDE** — Based on the results:
   - **BLOCK** if there are ANY api_errors OR ANY violations
   - **ESCALATE** if there are warnings but no violations/errors
   - **PROCEED** if everything is clean (no errors, violations, or warnings)

4. **ACT** based on your decision:

   If **BLOCK**:
   - Send blocked notification via `notify_blocked`
   - If invoice is OVERDUE, also send `notify_finance_overdue`
   - Do NOT provision

   If **ESCALATE**:
   - Send escalation notification via `notify_escalation`
   - Do NOT provision

   If **PROCEED**:
   - Use `provision_account` to create the tenant
     - The tier comes from CLM key_terms.sla_tier (default: "Starter")
     - The customer_name comes from the account Name
   - Send success notification via `notify_success`
   - Send CS manager email via `send_email`
   - Find the customer signatory from CLM (not StackAdapt) and send
     welcome email via `send_customer_welcome`

## DECISION RULES

These are strict business rules — not suggestions:

**Violations (BLOCK):**
- Account missing, deleted, or has no Id/Name
- Opportunity not in "Closed Won" stage
- CLM contract not SIGNED or EXECUTED (DRAFT, SENT, EXPIRED, VOIDED block)
- Invoice VOIDED or CANCELLED
- Account owner inactive or missing required fields (Id, Email, Username)
- Any API integration error from any system

**Warnings (ESCALATE):**
- Missing BillingCountry, Industry on account
- Invoice OVERDUE, OPEN, PENDING, or DRAFT status
- Missing opportunity Amount, CloseDate, or ContractId
- CLM contract has pending signatories
- Missing user Name, Title, Department

## OUTPUT FORMAT

Return a structured OnboardingResult with your decision, risk assessment,
all violations/warnings found, actions taken, and notifications sent.
Include the complete data you collected for audit purposes.

Be concise in your summary — 1-3 sentences about the onboarding status.
"""


# ---------------------------------------------------------------------------
# Agent definition
# ---------------------------------------------------------------------------

onboarding_agent = Agent(
    model=_select_model(),
    deps_type=OnboardingDeps,
    output_type=OnboardingResult,
    system_prompt=SYSTEM_PROMPT,
    retries=3,
)


# ---------------------------------------------------------------------------
# Salesforce tools
# ---------------------------------------------------------------------------

@onboarding_agent.tool
async def fetch_salesforce_account(
    ctx: RunContext[OnboardingDeps],
) -> dict:
    """
    Fetch account data from Salesforce CRM for the onboarding account.

    Uses the account ID from the current onboarding context automatically.
    Returns the full account record including Name, Industry, BillingCountry,
    OwnerId, and IsDeleted flag. Returns {"status": "API_ERROR", ...} on
    integration failure, or {"status": "NOT_FOUND"} if the account doesn't exist.
    """
    from app.integrations import salesforce

    account_id = ctx.deps.account_id
    log_event("tool.salesforce.get_account", account_id=account_id,
              correlation_id=ctx.deps.correlation_id)

    result = salesforce.get_account(account_id)
    if result is None:
        return {"status": "NOT_FOUND", "account_id": account_id}
    ctx.deps.collected_account = result
    return result


@onboarding_agent.tool
async def fetch_salesforce_user(
    ctx: RunContext[OnboardingDeps],
    user_id: str,
) -> dict:
    """
    Fetch user/owner data from Salesforce by user ID.

    Returns user details including Email, IsActive, Department, Title, ProfileId.
    The account owner must be active for onboarding to proceed.
    """
    from app.integrations import salesforce

    log_event("tool.salesforce.get_user", user_id=user_id,
              correlation_id=ctx.deps.correlation_id)

    result = salesforce.get_user(user_id)
    if result is None:
        return {"status": "NOT_FOUND", "user_id": user_id}
    ctx.deps.collected_user = result
    return result


@onboarding_agent.tool
async def fetch_salesforce_opportunity(
    ctx: RunContext[OnboardingDeps],
) -> dict:
    """
    Fetch the opportunity linked to the onboarding account.

    Uses the account ID from the current onboarding context automatically.
    Returns opportunity details including StageName (must be "Closed Won"),
    Amount, CloseDate, and ContractId. Returns {"status": "NOT_FOUND"} if
    no opportunity exists for this account.
    """
    from app.integrations import salesforce

    account_id = ctx.deps.account_id
    log_event("tool.salesforce.get_opportunity", account_id=account_id,
              correlation_id=ctx.deps.correlation_id)

    result = salesforce.get_opportunity_by_account(account_id)
    if result is None:
        return {"status": "NOT_FOUND", "account_id": account_id}
    ctx.deps.collected_opportunity = result
    return result


@onboarding_agent.tool
async def fetch_salesforce_contract(
    ctx: RunContext[OnboardingDeps],
) -> dict:
    """
    Fetch the Salesforce contract record linked to the onboarding account.

    Uses the account ID from the current onboarding context automatically.
    This is the CRM contract record (not the CLM contract).
    Returns contract details including Status and ownership.
    """
    from app.integrations import salesforce

    account_id = ctx.deps.account_id
    log_event("tool.salesforce.get_contract", account_id=account_id,
              correlation_id=ctx.deps.correlation_id)

    result = salesforce.get_contract_by_account(account_id)
    if result is None:
        return {"status": "NOT_FOUND", "account_id": account_id}
    ctx.deps.collected_contract = result
    return result


# ---------------------------------------------------------------------------
# CLM tools
# ---------------------------------------------------------------------------

@onboarding_agent.tool
async def fetch_clm_contract(
    ctx: RunContext[OnboardingDeps],
) -> dict:
    """
    Fetch CLM (Contract Lifecycle Management) contract for the onboarding account.

    Uses the account ID from the current onboarding context automatically.
    Returns contract status (EXECUTED, SIGNED, DRAFT, PENDING_SIGNATURE, etc.),
    signatories with sign status, effective/expiry dates, and key terms including
    sla_tier and payment_terms. Check for error statuses (AUTH_ERROR, SERVER_ERROR).
    """
    from app.integrations import clm

    account_id = ctx.deps.account_id
    log_event("tool.clm.get_contract", account_id=account_id,
              correlation_id=ctx.deps.correlation_id)

    result = clm.get_contract(account_id)
    ctx.deps.collected_clm = result
    return result


# ---------------------------------------------------------------------------
# NetSuite tools
# ---------------------------------------------------------------------------

@onboarding_agent.tool
async def fetch_netsuite_invoice(
    ctx: RunContext[OnboardingDeps],
) -> dict:
    """
    Fetch invoice/payment data from NetSuite for the onboarding account.

    Uses the account ID from the current onboarding context automatically.
    Returns invoice details including status (PAID, OPEN, OVERDUE, DRAFT,
    VOIDED, CANCELLED), total, amount_remaining, due_date, and days_overdue.
    Check for error statuses (AUTH_ERROR, SERVER_ERROR).
    """
    from app.integrations import netsuite

    account_id = ctx.deps.account_id
    log_event("tool.netsuite.get_invoice", account_id=account_id,
              correlation_id=ctx.deps.correlation_id)

    result = netsuite.get_invoice(account_id)
    ctx.deps.collected_invoice = result
    return result


# ---------------------------------------------------------------------------
# Validation tools
# ---------------------------------------------------------------------------

@onboarding_agent.tool
async def validate_business_rules(
    ctx: RunContext[OnboardingDeps],
) -> dict:
    """
    Run all business rule validations on the data collected by fetch tools.

    Call this AFTER fetching data from all systems. It automatically uses the
    complete, unmodified data stored by each fetch tool — no arguments needed.

    Returns: {"violations": {...}, "warnings": {...}}
    """
    from app.agent.invariants import (
        check_account_invariants,
        check_user_invariants,
        check_opportunity_invariants,
        check_contract_invariants,
        check_invoice_invariants,
    )

    log_event("tool.validation.run_all", account_id=ctx.deps.account_id,
              correlation_id=ctx.deps.correlation_id)

    # Auto-fetch user if account has OwnerId but user wasn't fetched
    if ctx.deps.collected_user is None and ctx.deps.collected_account:
        owner_id = ctx.deps.collected_account.get("OwnerId")
        if owner_id:
            from app.integrations import salesforce
            user_data = salesforce.get_user(owner_id)
            if user_data:
                ctx.deps.collected_user = user_data

    # Use the complete data stored by fetch tools — avoids LLM data truncation
    state: Dict[str, Any] = {
        "account": ctx.deps.collected_account,
        "user": ctx.deps.collected_user,
        "opportunity": ctx.deps.collected_opportunity,
        "contract": ctx.deps.collected_contract,
        "invoice": ctx.deps.collected_invoice,
        "clm": ctx.deps.collected_clm,
        "violations": {},
        "warnings": {},
    }

    check_account_invariants(state)
    check_user_invariants(state)
    check_opportunity_invariants(state)
    check_contract_invariants(state)
    check_invoice_invariants(state)

    return {
        "violations": state.get("violations", {}),
        "warnings": state.get("warnings", {}),
    }


# ---------------------------------------------------------------------------
# Provisioning tools
# ---------------------------------------------------------------------------

@onboarding_agent.tool
async def provision_account(
    ctx: RunContext[OnboardingDeps],
    account_id: str,
    tier: str = "Starter",
    customer_name: str = "Customer",
) -> dict:
    """
    Provision a new tenant in the SaaS platform.

    ONLY call this when the decision is PROCEED (no violations, no API errors).

    Creates a tenant with: tenant ID, API credentials, admin URL, and a full
    onboarding task checklist (14 tasks). The tier determines features and limits:
    - Enterprise: SSO, custom reports, 100 users, 500GB
    - Growth: standard reports, 25 users, 100GB
    - Starter: basic reports, 5 users, 25GB
    """
    from app.integrations import provisioning

    log_event("tool.provisioning.provision", account_id=account_id,
              tier=tier, correlation_id=ctx.deps.correlation_id)

    return provisioning.provision_account(account_id, tier, customer_name)


# ---------------------------------------------------------------------------
# Notification tools
# ---------------------------------------------------------------------------

@onboarding_agent.tool
async def notify_blocked(
    ctx: RunContext[OnboardingDeps],
    account_name: str,
    account_id: str,
    violations: dict,
) -> dict:
    """
    Send urgent Slack alert when onboarding is BLOCKED.
    Notifies #cs-onboarding-alerts with violation details.
    """
    from app.notifications import notifier

    log_event("tool.notify.blocked", account_id=account_id,
              correlation_id=ctx.deps.correlation_id)

    return notifier.notify_cs_team_blocked(
        account_name=account_name,
        account_id=account_id,
        violations=violations,
        correlation_id=ctx.deps.correlation_id,
    )


@onboarding_agent.tool
async def notify_escalation(
    ctx: RunContext[OnboardingDeps],
    account_name: str,
    account_id: str,
    warnings: dict,
) -> dict:
    """
    Send Slack notification for human review when onboarding is ESCALATED.
    Notifies #cs-onboarding with warning details.
    """
    from app.notifications import notifier

    log_event("tool.notify.escalation", account_id=account_id,
              correlation_id=ctx.deps.correlation_id)

    return notifier.notify_cs_team_escalation(
        account_name=account_name,
        account_id=account_id,
        warnings=warnings,
        correlation_id=ctx.deps.correlation_id,
    )


@onboarding_agent.tool
async def notify_success(
    ctx: RunContext[OnboardingDeps],
    account_name: str,
    account_id: str,
    tenant_id: str,
) -> dict:
    """
    Send Slack confirmation when onboarding completes successfully.
    Notifies #cs-onboarding with tenant details.
    """
    from app.notifications import notifier

    log_event("tool.notify.success", account_id=account_id,
              correlation_id=ctx.deps.correlation_id)

    return notifier.notify_cs_team_success(
        account_name=account_name,
        account_id=account_id,
        tenant_id=tenant_id,
        correlation_id=ctx.deps.correlation_id,
    )


@onboarding_agent.tool
async def notify_finance_overdue(
    ctx: RunContext[OnboardingDeps],
    account_name: str,
    account_id: str,
    invoice_id: str,
    amount: float,
    days_overdue: int,
) -> dict:
    """
    Escalate overdue invoice to finance team via #finance-alerts Slack channel.
    Use when an invoice is OVERDUE and impacting onboarding.
    """
    from app.notifications import notifier

    log_event("tool.notify.finance_overdue", account_id=account_id,
              correlation_id=ctx.deps.correlation_id)

    return notifier.notify_finance_overdue_invoice(
        account_name=account_name,
        account_id=account_id,
        invoice_id=invoice_id,
        amount=amount,
        days_overdue=days_overdue,
        correlation_id=ctx.deps.correlation_id,
    )


@onboarding_agent.tool
async def send_customer_welcome(
    ctx: RunContext[OnboardingDeps],
    customer_email: str,
    customer_name: str,
    account_name: str,
    tenant_id: str,
    account_id: str,
) -> dict:
    """
    Send welcome email to the customer with login instructions.
    Use after successful provisioning. Find the customer signatory
    from CLM data (the one NOT from StackAdapt).
    """
    from app.notifications import notifier

    log_event("tool.notify.customer_welcome", account_id=account_id,
              correlation_id=ctx.deps.correlation_id)

    return notifier.send_customer_welcome_email(
        customer_email=customer_email,
        customer_name=customer_name,
        account_name=account_name,
        tenant_id=tenant_id,
        account_id=account_id,
        correlation_id=ctx.deps.correlation_id,
    )


@onboarding_agent.tool
async def send_email(
    ctx: RunContext[OnboardingDeps],
    to: str,
    subject: str,
    body: str,
) -> dict:
    """Send a generic email notification."""
    from app.notifications import notifier

    log_event("tool.notify.email", to=to,
              correlation_id=ctx.deps.correlation_id)

    return notifier.send_email(
        to=to,
        subject=subject,
        body=body,
        account_id=ctx.deps.account_id,
        correlation_id=ctx.deps.correlation_id,
    )

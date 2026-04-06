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

1. **GATHER DATA** — You MUST fetch data from ALL systems before validating.
   Data flows sequentially: Sales → Contract → CLM → Invoice. Each system's
   output provides lookup keys for the next system in the chain.

   a) Call `fetch_salesforce_account` (no args — uses onboarding context)
   b) Call `fetch_salesforce_user` with the OwnerId from the account result
   c) Call `fetch_salesforce_opportunity` (no args — uses account context)
   d) Call `fetch_salesforce_contract` — pass `contract_id` from the
      Opportunity's ContractId field if available (enables direct lookup
      instead of account-based search)
   e) Call `fetch_clm_contract` — pass `salesforce_contract_id` from the
      SF Contract's Id field if available (chains CRM → CLM lookup)
   f) Call `fetch_netsuite_invoice` — pass `clm_contract_ref` from the
      CLM contract's contract_id field if available (chains CLM → ERP lookup)
   g) Optionally call `convert_currency` to convert invoice amounts to CAD
      (StackAdapt is a Canadian company — CAD context is useful)

   Steps b-c can run in parallel after step a. Steps d→e→f are sequential
   because each uses the previous step's output as a lookup key. If a
   chaining parameter is not available (e.g., Opportunity has no ContractId),
   omit it — the tool will fall back to account-based lookup automatically.

   You MUST call ALL fetch tools before calling validate_business_rules.

   IMPORTANT: If any fetch returns a response with "status": "API_ERROR"
   or similar error status (AUTH_ERROR, SERVER_ERROR, etc.), record it
   as an API error. API errors are BLOCKING — they prevent onboarding.

2. **VALIDATE** — Once data is gathered:
   a) Call `validate_business_rules` with NO arguments. It automatically
      uses the data collected by the fetch tools. Returns violations
      (blocking), warnings (non-blocking), and a `decision_guidance` field
      that tells you BLOCK, ESCALATE, or PROCEED.
   b) Call `check_financial_alignment` with NO arguments. It compares the
      opportunity deal value against the invoice total (converting currencies
      if needed) and checks for underpayment gaps. Uses a 2% threshold.
      Its warnings are added to the warning count (non-blocking).

3. **DECIDE** — Follow the `decision_guidance` from `validate_business_rules`.
   The tool computes the correct decision based on its rules. You MUST
   follow it unless there are also api_errors from fetch tools.

   - If `decision_guidance` says BLOCK → your decision is **BLOCK**
   - If `decision_guidance` says ESCALATE → your decision is **ESCALATE**
     (even if check_financial_alignment adds more warnings, it stays ESCALATE)
   - If `decision_guidance` says PROCEED but check_financial_alignment's
     `decision_guidance` says ESCALATE → upgrade to **ESCALATE**
   - If both `decision_guidance` fields say PROCEED → **PROCEED**
   - If ANY fetch tool returned an api_error status → override to **BLOCK**

   CRITICAL: Do NOT reclassify warnings as violations. The tool's
   `has_violations` and `has_warnings` fields are authoritative.
   An overdue invoice is a WARNING. A missing BillingCountry is a WARNING.
   A missing ContractId is a WARNING. Trust the tool output.

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

These rules are enforced by `validate_business_rules`. Do NOT override them.
Use the tool's "violations" and "warnings" output as-is for your decision.

**Items that appear as VIOLATIONS (→ BLOCK):**
- Account missing, deleted, or has no Id/Name
- Opportunity not in "Closed Won" stage
- CLM contract not SIGNED or EXECUTED (DRAFT, SENT, EXPIRED, VOIDED block)
- Invoice VOIDED or CANCELLED
- Account owner inactive or missing required fields (Id, Email, Username)
- Any API integration error from any system

**Items that appear as WARNINGS (→ ESCALATE, NOT block):**
- Missing BillingCountry, Industry on account
- Invoice OVERDUE, OPEN, PENDING, or DRAFT status
- Missing opportunity Amount, CloseDate, or ContractId
- CLM contract has pending signatories
- Missing user Name, Title, Department
- Financial alignment gaps from check_financial_alignment

An overdue invoice is a WARNING, not a violation. A missing BillingCountry
is a WARNING, not a violation. A missing ContractId on a Closed Won
opportunity is a WARNING, not a violation. Trust the tool output.

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
    contract_id: str = "",
) -> dict:
    """
    Fetch the Salesforce contract record (CRM contract, not CLM).

    Data chaining: pass `contract_id` from the Opportunity's ContractId
    field for a direct lookup. If omitted, falls back to account-based search.
    Returns contract details including Status and ownership.
    """
    from app.integrations import salesforce

    account_id = ctx.deps.account_id

    result = None

    if contract_id:
        log_event("tool.salesforce.get_contract", contract_id=contract_id,
                  correlation_id=ctx.deps.correlation_id)
        result = salesforce.get_contract(contract_id)

    # Fall back to account-based lookup if chain missed
    if result is None:
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
    salesforce_contract_id: str = "",
) -> dict:
    """
    Fetch CLM (Contract Lifecycle Management) contract.

    Data chaining: pass `salesforce_contract_id` from the SF Contract's Id
    field for a cross-system lookup (CRM → CLM). If omitted, falls back to
    account-based search. Returns contract status (EXECUTED, SIGNED, DRAFT,
    PENDING_SIGNATURE, etc.), signatories, effective/expiry dates, and key
    terms including sla_tier and payment_terms.
    """
    from app.integrations import clm

    account_id = ctx.deps.account_id

    result = None

    if salesforce_contract_id:
        log_event("tool.clm.get_contract_by_sf_id",
                  salesforce_contract_id=salesforce_contract_id,
                  correlation_id=ctx.deps.correlation_id)
        result = clm.get_contract_by_sf_contract_id(salesforce_contract_id)

    # Fall back to account-based lookup if chain missed or returned NOT_FOUND
    if not result or result.get("status") == "NOT_FOUND":
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
    clm_contract_ref: str = "",
) -> dict:
    """
    Fetch invoice/payment data from NetSuite.

    Data chaining: pass `clm_contract_ref` from the CLM contract's
    contract_id field for a cross-system lookup (CLM → ERP). If omitted,
    falls back to account-based search. Returns invoice details including
    status (PAID, OPEN, OVERDUE, DRAFT, VOIDED, CANCELLED), total,
    amount_remaining, due_date, and days_overdue.
    """
    from app.integrations import netsuite

    account_id = ctx.deps.account_id

    result = None

    if clm_contract_ref:
        log_event("tool.netsuite.get_invoice_by_clm_ref",
                  clm_contract_ref=clm_contract_ref,
                  correlation_id=ctx.deps.correlation_id)
        result = netsuite.get_invoice_by_clm_ref(clm_contract_ref)

    # Fall back to account-based lookup if chain missed or returned NOT_FOUND
    if not result or result.get("status") == "NOT_FOUND":
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

    violations = state.get("violations", {})
    warnings = state.get("warnings", {})
    has_violations = any(violations.values())
    has_warnings = any(warnings.values())

    if has_violations:
        decision_guidance = "BLOCK — violations found (these are blocking issues)"
    elif has_warnings:
        decision_guidance = "ESCALATE — warnings found but NO violations (non-blocking, needs review)"
    else:
        decision_guidance = "PROCEED — no violations and no warnings"

    return {
        "violations": violations,
        "warnings": warnings,
        "decision_guidance": decision_guidance,
        "has_violations": has_violations,
        "has_warnings": has_warnings,
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


# ---------------------------------------------------------------------------
# Currency tools
# ---------------------------------------------------------------------------

@onboarding_agent.tool
async def convert_currency(
    ctx: RunContext[OnboardingDeps],
    amount: float,
    from_currency: str,
    to_currency: str,
    date: str = "",
) -> dict:
    """
    Convert a monetary amount between currencies using exchange rates.

    Useful for converting USD invoice totals to CAD (StackAdapt's home
    currency). Uses the European Central Bank's published rates via the
    Frankfurter API — no API key required.

    Supports historical rates: pass a date (YYYY-MM-DD) to get the rate
    from that date (e.g. the invoice or payment date). If no date is
    provided, uses the latest available rate.

    Args:
        amount: The monetary amount to convert.
        from_currency: Source currency code (e.g. "USD").
        to_currency: Target currency code (e.g. "CAD").
        date: Optional date (YYYY-MM-DD) for historical rate lookup.
    """
    from app.integrations import currency

    log_event(
        "tool.currency.convert",
        amount=amount,
        from_currency=from_currency,
        to_currency=to_currency,
        date=date or "latest",
        correlation_id=ctx.deps.correlation_id,
    )

    return currency.convert_currency(
        amount, from_currency, to_currency, date=date or None,
    )


# ---------------------------------------------------------------------------
# Financial alignment tools
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Post-provisioning monitoring tools (CS assistant mode)
# ---------------------------------------------------------------------------

@onboarding_agent.tool
async def check_onboarding_progress(
    ctx: RunContext[OnboardingDeps],
    account_id: str,
) -> dict:
    """
    Get a dashboard view of onboarding progress for a provisioned account.

    Returns completion %, task breakdown by status, overdue/blocked counts,
    days since provisioning, and a health_status (on_track / at_risk / stalled).
    """
    from app.integrations import provisioning

    log_event("tool.provisioning.check_progress", account_id=account_id,
              correlation_id=ctx.deps.correlation_id)
    return provisioning.check_onboarding_progress(account_id)


@onboarding_agent.tool
async def identify_onboarding_risks(
    ctx: RunContext[OnboardingDeps],
    account_id: str,
) -> dict:
    """
    Detect risks and problems needing CS attention for a provisioned account.

    Checks for: customer not logged in after 3 days, SSO not configured after
    kickoff, tasks blocked, onboarding stalling (<30% after 7 days), customer
    actions overdue.
    """
    from app.integrations import provisioning

    log_event("tool.provisioning.identify_risks", account_id=account_id,
              correlation_id=ctx.deps.correlation_id)
    return provisioning.identify_onboarding_risks(account_id)


@onboarding_agent.tool
async def send_task_reminder(
    ctx: RunContext[OnboardingDeps],
    account_id: str,
    task_id: str,
    recipient: str = "",
    message: str = "",
) -> dict:
    """
    Send a reminder about a pending onboarding task to the assigned owner.

    Use when a task is overdue or at risk of being missed.
    """
    from app.integrations import provisioning

    log_event("tool.provisioning.send_reminder", account_id=account_id,
              task_id=task_id, correlation_id=ctx.deps.correlation_id)
    return provisioning.send_task_reminder(account_id, task_id, recipient, message)


@onboarding_agent.tool
async def escalate_stalled_onboarding(
    ctx: RunContext[OnboardingDeps],
    account_id: str,
    reason: str = "",
) -> dict:
    """
    Escalate a stalled onboarding to CS management.

    Posts to #cs-onboarding-escalations with progress details. Use when
    onboarding is stalled (blocked tasks, low completion after many days).
    """
    from app.integrations import provisioning

    log_event("tool.provisioning.escalate", account_id=account_id,
              correlation_id=ctx.deps.correlation_id)
    return provisioning.escalate_stalled_onboarding(account_id, reason)


@onboarding_agent.tool
async def update_onboarding_task(
    ctx: RunContext[OnboardingDeps],
    account_id: str,
    task_id: str,
    status: str,
    notes: str = "",
) -> dict:
    """
    Update the status of an onboarding task.

    Valid statuses: pending, in_progress, completed, blocked, skipped.
    Use to mark tasks as done, flag blockers, or skip inapplicable tasks.
    """
    from app.integrations import provisioning

    log_event("tool.provisioning.update_task", account_id=account_id,
              task_id=task_id, status=status,
              correlation_id=ctx.deps.correlation_id)
    return provisioning.update_task_status(
        account_id, task_id, status, completed_by="cs_assistant", notes=notes or None
    )


# ---------------------------------------------------------------------------
# Financial alignment tools
# ---------------------------------------------------------------------------

FINANCIAL_ALIGNMENT_THRESHOLD = 0.02  # 2%


@onboarding_agent.tool
async def check_financial_alignment(
    ctx: RunContext[OnboardingDeps],
) -> dict:
    """
    Check financial alignment between opportunity deal value and invoice.

    Call this AFTER fetching opportunity and invoice data. It automatically
    reads from the collected data — no arguments needed.

    Performs two checks with a 2% tolerance threshold:
    1. Opportunity Amount vs Invoice Total (converts currencies if different)
    2. Invoice Amount Paid vs Invoice Total (detects underpayment)

    Returns warnings (not violations) for any gaps exceeding the threshold.
    """
    from app.integrations import currency

    log_event(
        "tool.financial_alignment.check",
        account_id=ctx.deps.account_id,
        correlation_id=ctx.deps.correlation_id,
    )

    opportunity = ctx.deps.collected_opportunity
    invoice = ctx.deps.collected_invoice
    warnings = []
    details = {}

    # --- Check 1: Opportunity Amount vs Invoice Total ---
    if opportunity and invoice:
        opp_amount = opportunity.get("Amount")
        inv_total = invoice.get("total")
        inv_currency = invoice.get("currency", "USD")
        opp_currency = "USD"  # Salesforce opportunities are in USD

        # Use the invoice date for historical rate lookup so the conversion
        # reflects the rate at the time of payment, not today's rate.
        inv_date = invoice.get("invoice_date")

        if opp_amount and inv_total:
            normalized_inv_total = inv_total

            if inv_currency != opp_currency:
                conversion = currency.convert_currency(
                    inv_total, inv_currency, opp_currency, date=inv_date,
                )
                if conversion.get("status") == "OK":
                    normalized_inv_total = conversion["converted_amount"]
                    details["currency_conversion"] = {
                        "from": inv_currency,
                        "to": opp_currency,
                        "rate": conversion["rate"],
                        "rate_date": conversion.get("date", ""),
                        "original_amount": inv_total,
                        "converted_amount": normalized_inv_total,
                    }

            gap = abs(normalized_inv_total - opp_amount)
            gap_pct = gap / opp_amount if opp_amount else 0

            details["opportunity_vs_invoice"] = {
                "opportunity_amount": opp_amount,
                "invoice_total": inv_total,
                "invoice_currency": inv_currency,
                "normalized_invoice_total": normalized_inv_total,
                "gap_amount": round(gap, 2),
                "gap_percentage": round(gap_pct * 100, 2),
                "threshold_percentage": FINANCIAL_ALIGNMENT_THRESHOLD * 100,
                "within_threshold": gap_pct <= FINANCIAL_ALIGNMENT_THRESHOLD,
            }

            if gap_pct > FINANCIAL_ALIGNMENT_THRESHOLD:
                warnings.append(
                    f"Invoice total ({inv_currency} {inv_total:,.2f} = "
                    f"USD {normalized_inv_total:,.2f}) differs from opportunity "
                    f"amount (USD {opp_amount:,.2f}) by {gap_pct*100:.1f}% "
                    f"(exceeds {FINANCIAL_ALIGNMENT_THRESHOLD*100:.0f}% threshold)"
                )

    # --- Check 2: Invoice Paid vs Total ---
    if invoice:
        inv_total = invoice.get("total", 0)
        inv_paid = invoice.get("amount_paid", 0)

        if inv_total and inv_total > 0:
            paid_gap = inv_total - inv_paid
            paid_gap_pct = paid_gap / inv_total if inv_total else 0

            details["paid_vs_total"] = {
                "invoice_total": inv_total,
                "amount_paid": inv_paid,
                "amount_remaining": round(paid_gap, 2),
                "unpaid_percentage": round(paid_gap_pct * 100, 2),
                "threshold_percentage": FINANCIAL_ALIGNMENT_THRESHOLD * 100,
                "within_threshold": paid_gap_pct <= FINANCIAL_ALIGNMENT_THRESHOLD,
            }

            if paid_gap_pct > FINANCIAL_ALIGNMENT_THRESHOLD:
                warnings.append(
                    f"Invoice underpayment: {paid_gap_pct*100:.1f}% unpaid "
                    f"(${paid_gap:,.2f} remaining of ${inv_total:,.2f} total, "
                    f"exceeds {FINANCIAL_ALIGNMENT_THRESHOLD*100:.0f}% threshold)"
                )

    log_event(
        "tool.financial_alignment.result",
        account_id=ctx.deps.account_id,
        warnings_count=len(warnings),
        correlation_id=ctx.deps.correlation_id,
    )

    has_warnings = len(warnings) > 0
    if has_warnings:
        decision_guidance = (
            "ESCALATE — financial alignment warnings found "
            "(these are non-blocking but require CS/Finance review)"
        )
    else:
        decision_guidance = "PROCEED — financials aligned, no issues detected"

    return {
        "status": "OK",
        "warnings": warnings,
        "details": details,
        "decision_guidance": decision_guidance,
        "has_warnings": has_warnings,
    }


# ---------------------------------------------------------------------------
# CS Assistant Agent (free-form text for chat interactions)
# ---------------------------------------------------------------------------

CS_ASSISTANT_PROMPT = """\
You are a Customer Success assistant for StackAdapt. You help CS managers
monitor and manage customer onboardings by answering questions and taking
actions using the tools available to you.

## CAPABILITIES

You can:
- **Check onboarding progress** — completion %, health status, overdue tasks
- **Identify risks** — detect problems that need attention
- **Send reminders** — nudge customers or CS team about pending tasks
- **Update tasks** — mark tasks as completed, blocked, or in progress
- **Escalate** — flag stalled onboardings to CS management
- **Run new onboardings** — fetch data, validate, and process new accounts
- **Check financials** — verify deal/invoice alignment

## INTERACTION STYLE

- Be concise and actionable — CS managers are busy
- When showing progress, highlight what needs attention first
- Proactively suggest next steps based on what you find
- If you detect risks, recommend specific actions
- Use the account_id the user provides (e.g., "ACME-001")

## EXAMPLES

User: "What's the status of ACME-001's onboarding?"
→ Use check_onboarding_progress, then summarize with next actions

User: "Are there any risks with ACME-001?"
→ Use identify_onboarding_risks, then recommend actions

User: "Send a reminder about the login task"
→ Use send_task_reminder with the relevant task ID

User: "Onboard BETA-002"
→ Run the full onboarding workflow (fetch → validate → decide → act)
"""

cs_assistant_agent = Agent(
    model=_select_model(),
    deps_type=OnboardingDeps,
    output_type=str,
    system_prompt=CS_ASSISTANT_PROMPT,
    retries=3,
)

# Share all tools from the onboarding agent with the CS assistant
# by registering the same tool functions
for _tool_name, _tool_def in onboarding_agent._function_toolset.tools.items():
    cs_assistant_agent._function_toolset.tools[_tool_name] = _tool_def

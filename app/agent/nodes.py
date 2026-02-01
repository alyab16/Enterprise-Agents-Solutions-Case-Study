"""
Agent nodes - individual processing steps in the onboarding workflow.
Each node performs a specific task and updates the agent state.
"""

from app.agent.state import AgentState
from app.agent.state_utils import record_action, record_notification, add_api_error, add_violation
from app.integrations import salesforce, clm, netsuite, provisioning
from app.agent.invariants import (
    check_account_invariants,
    check_opportunity_invariants,
    check_contract_invariants,
    check_user_invariants,
    check_invoice_invariants,
)
from app.llm.risk_analyzer import analyze_risks, generate_summary
from app.notifications import notifier
from app.logging.logger import log_event, log_state_transition


def init_node(state: AgentState) -> AgentState:
    """Initialize the onboarding run."""
    log_event(
        "node.init",
        account_id=state.get("account_id"),
        correlation_id=state.get("correlation_id"),
    )
    
    state["stage"] = "initializing"
    state["violations"] = {}
    state["warnings"] = {}
    state["actions_taken"] = []
    state["notifications_sent"] = []
    state["api_errors"] = []  # Initialize API errors list
    
    return state


def fetch_salesforce_data(state: AgentState) -> AgentState:
    """Fetch all relevant data from Salesforce."""
    account_id = state.get("account_id")

    log_state_transition(
        from_stage=state.get("stage"),
        to_stage="fetching_salesforce",
        account_id=account_id,
        correlation_id=state.get("correlation_id"),
    )
    state["stage"] = "fetching_salesforce"

    # ------------------------------------------------------------------
    # Fetch Account
    # ------------------------------------------------------------------
    account = salesforce.get_account(account_id)

    # 🚨 Handle Salesforce API error (DO NOT SWALLOW)
    if isinstance(account, dict) and account.get("status") == "API_ERROR":
        add_api_error(
            state,
            system="salesforce",
            error_type=account["error_type"],
            error_code=account["error_code"],
            message=account["message"],
            http_status=account.get("http_status", 0),
            details=account.get("details", {}),
        )
        return state

    # Legitimate not-found (business logic)
    if account is None:
        add_violation(
            state,
            "salesforce",
            f"Account {account_id} not found in Salesforce"
        )
        return state

    # Success path
    state["account"] = account

    # ------------------------------------------------------------------
    # Fetch Account Owner (User)
    # ------------------------------------------------------------------
    owner_id = account.get("OwnerId")
    if owner_id:
        user = salesforce.get_user(owner_id)

        # 🚨 Handle Salesforce API error
        if isinstance(user, dict) and user.get("status") == "API_ERROR":
            add_api_error(
                state,
                system="salesforce",
                error_type=user["error_type"],
                error_code=user["error_code"],
                message=user["message"],
                http_status=user.get("http_status", 0),
                details=user.get("details", {}),
            )
            return state

        # Legitimate not-found (user missing)
        if user is None:
            add_violation(
                state,
                "salesforce",
                f"Owner user {owner_id} not found in Salesforce"
            )
            return state

        state["user"] = user

    # ------------------------------------------------------------------
    # Fetch Opportunity (mock lookup – no API errors)
    # ------------------------------------------------------------------
    state["opportunity"] = salesforce.get_opportunity_by_account(account_id)

    # ------------------------------------------------------------------
    # Fetch Contract (mock lookup – no API errors)
    # ------------------------------------------------------------------
    state["contract"] = salesforce.get_contract_by_account(account_id)

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------
    log_event(
        "salesforce.fetched",
        account_id=account_id,
        has_account=True,
        has_user=state.get("user") is not None,
        has_opportunity=state.get("opportunity") is not None,
        has_contract=state.get("contract") is not None,
        api_errors=len(state.get("api_errors", [])),
    )

    return state


def fetch_clm_data(state: AgentState) -> AgentState:
    """Fetch contract status from CLM system."""
    account_id = state.get("account_id")

    log_state_transition(
        from_stage=state.get("stage"),
        to_stage="fetching_clm",
        account_id=account_id,
        correlation_id=state.get("correlation_id"),
    )
    state["stage"] = "fetching_clm"

    clm_data = clm.get_contract(account_id)

    # 🚨 Handle CLM API errors (DO NOT SWALLOW)
    if isinstance(clm_data, dict) and clm_data.get("status") in {
        "AUTH_ERROR",
        "PERMISSION_ERROR",
        "SERVER_ERROR",
        "API_ERROR",
    }:
        error_type_map = {
            "AUTH_ERROR": ("authentication", "UNAUTHORIZED", 401),
            "PERMISSION_ERROR": ("authorization", "FORBIDDEN", 403),
            "SERVER_ERROR": ("server", "INTERNAL_ERROR", 500),
            "API_ERROR": ("server", "API_ERROR", 500),
        }

        error_type, error_code, http_status = error_type_map.get(
            clm_data.get("status"),
            ("server", "UNKNOWN", 500),
        )

        add_api_error(
            state,
            system="clm",
            error_type=error_type,
            error_code=error_code,
            message=clm_data.get("error", "CLM API error"),
            http_status=http_status,
            details={
                "account_id": account_id,
                "operation": "get_contract",
                "clm_status": clm_data.get("status"),
            },
        )
        return state

    # Legitimate no-contract case (business logic)
    if clm_data is None:
        add_violation(
            state,
            "clm",
            f"No CLM contract found for account {account_id}"
        )
        return state

    # Success path
    state["clm"] = clm_data

    log_event(
        "clm.fetched",
        account_id=account_id,
        clm_status=clm_data.get("status"),
        api_errors=len(state.get("api_errors", [])),
    )

    return state


def fetch_invoice_data(state: AgentState) -> AgentState:
    """Fetch invoice status from NetSuite."""
    account_id = state.get("account_id")

    log_state_transition(
        from_stage=state.get("stage"),
        to_stage="fetching_invoice",
        account_id=account_id,
        correlation_id=state.get("correlation_id"),
    )
    state["stage"] = "fetching_invoice"

    invoice = netsuite.get_invoice(account_id)

    # 🚨 Handle NetSuite API errors (DO NOT SWALLOW)
    if isinstance(invoice, dict) and invoice.get("status") in {
        "AUTH_ERROR",
        "PERMISSION_ERROR",
        "VALIDATION_ERROR",
        "SERVER_ERROR",
        "API_ERROR",
    }:
        error_type_map = {
            "AUTH_ERROR": ("authentication", "INVALID_LOGIN", 401),
            "PERMISSION_ERROR": ("authorization", "INSUFFICIENT_PERMISSION", 403),
            "VALIDATION_ERROR": ("validation", "INVALID_FIELD_VALUE", 400),
            "SERVER_ERROR": ("server", "UNEXPECTED_ERROR", 500),
            "API_ERROR": ("server", "API_ERROR", 500),
        }

        error_type, error_code, http_status = error_type_map.get(
            invoice.get("status"),
            ("server", "UNKNOWN", 500),
        )

        add_api_error(
            state,
            system="netsuite",
            error_type=error_type,
            error_code=error_code,
            message=invoice.get("error", "NetSuite API error"),
            http_status=http_status,
            details={
                "account_id": account_id,
                "operation": "get_invoice",
                "invoice_id": invoice.get("invoice_id"),
                "error_details": invoice.get("error_details", {}),
            },
        )
        return state

    # Legitimate no-invoice case (business logic)
    if invoice is None:
        add_violation(
            state,
            "netsuite",
            f"No invoice found for account {account_id}"
        )
        return state

    # Success path
    state["invoice"] = invoice

    log_event(
        "invoice.fetched",
        account_id=account_id,
        invoice_status=invoice.get("status"),
        api_errors=len(state.get("api_errors", [])),
    )

    return state


def validate_data(state: AgentState) -> AgentState:
    """Run all invariant checks on the collected data."""
    account_id = state.get("account_id")
    
    log_state_transition(
        from_stage=state.get("stage"),
        to_stage="validating",
        account_id=account_id,
        correlation_id=state.get("correlation_id"),
    )
    state["stage"] = "validating"
    
    # Run all invariant checks
    check_account_invariants(state)
    check_user_invariants(state)
    check_opportunity_invariants(state)
    check_contract_invariants(state)
    check_invoice_invariants(state)
    
    violation_count = sum(len(msgs) for msgs in state.get("violations", {}).values())
    warning_count = sum(len(msgs) for msgs in state.get("warnings", {}).values())
    
    log_event(
        "validation.complete",
        account_id=account_id,
        violations=violation_count,
        warnings=warning_count,
    )
    
    return state


def analyze_risks_node(state: AgentState) -> AgentState:
    """Use LLM to analyze risks and generate recommendations."""
    account_id = state.get("account_id")
    
    log_state_transition(
        from_stage=state.get("stage"),
        to_stage="analyzing_risks",
        account_id=account_id,
        correlation_id=state.get("correlation_id"),
    )
    state["stage"] = "analyzing_risks"
    
    # Run LLM risk analysis
    risk_analysis = analyze_risks(state)
    state["risk_analysis"] = risk_analysis
    state["recommended_actions"] = [
        a["action"] for a in risk_analysis.get("recommended_actions", [])
    ]
    
    log_event(
        "risk_analysis.complete",
        account_id=account_id,
        risk_level=risk_analysis.get("risk_level"),
        can_proceed=risk_analysis.get("can_proceed_with_warnings"),
    )
    
    return state


def make_decision(state: AgentState) -> AgentState:
    """Determine the routing decision based on violations, warnings, AND api_errors."""
    account_id = state.get("account_id")
    violations = state.get("violations", {})
    warnings = state.get("warnings", {})
    api_errors = state.get("api_errors", [])
    
    violation_count = sum(len(msgs) for msgs in violations.values())
    warning_count = sum(len(msgs) for msgs in warnings.values())
    api_error_count = len(api_errors)
    
    # API errors are blocking - they indicate system failures that prevent onboarding
    if api_error_count > 0:
        state["decision"] = "BLOCK"
        state["stage"] = "blocked"
        # Add API errors as violations so they appear in the report
        for error in api_errors:
            system = error.get("system", "api")
            error_type = error.get("error_type", "unknown")
            message = error.get("message", "API error occurred")
            error_code = error.get("error_code", "UNKNOWN")
            violations.setdefault(system, []).append(
                f"API Error ({error_type}): {message} [Code: {error_code}]"
            )
        state["violations"] = violations
    elif violation_count > 0:
        state["decision"] = "BLOCK"
        state["stage"] = "blocked"
    elif warning_count > 0:
        state["decision"] = "ESCALATE"
        state["stage"] = "escalation_required"
    else:
        state["decision"] = "PROCEED"
        state["stage"] = "ready_to_provision"
    
    log_event(
        "decision.made",
        account_id=account_id,
        decision=state["decision"],
        violations=violation_count,
        warnings=warning_count,
        api_errors=api_error_count,
    )
    
    return state


def send_notifications(state: AgentState) -> AgentState:
    """Send appropriate notifications based on the decision."""
    account_id = state.get("account_id")
    correlation_id = state.get("correlation_id", "")
    decision = state.get("decision")
    account = state.get("account") or {}
    account_name = account.get("Name", account_id)
    
    log_state_transition(
        from_stage=state.get("stage"),
        to_stage="sending_notifications",
        account_id=account_id,
        correlation_id=correlation_id,
    )
    
    if decision == "BLOCK":
        # Send urgent notification to CS team
        notifier.notify_cs_team_blocked(
            account_name=account_name,
            account_id=account_id,
            violations=state.get("violations", {}),
            correlation_id=correlation_id,
        )
        record_notification(
            state, "slack", "#cs-onboarding-alerts",
            f"Blocked notification sent for {account_name}"
        )
        
        # Check if invoice issue - escalate to finance
        invoice = state.get("invoice") or {}
        if invoice.get("status") == "OVERDUE":
            notifier.notify_finance_overdue_invoice(
                account_name=account_name,
                account_id=account_id,
                invoice_id=invoice.get("invoice_id", ""),
                amount=invoice.get("amount_remaining", invoice.get("total", 0)),
                days_overdue=invoice.get("days_overdue", 0),
                correlation_id=correlation_id,
            )
            record_notification(
                state, "slack", "#finance-alerts",
                f"Overdue invoice escalation for {account_name}"
            )
    
    elif decision == "ESCALATE":
        # Send notification for human review
        notifier.notify_cs_team_escalation(
            account_name=account_name,
            account_id=account_id,
            warnings=state.get("warnings", {}),
            correlation_id=correlation_id,
        )
        record_notification(
            state, "slack", "#cs-onboarding",
            f"Escalation notification sent for {account_name}"
        )
    
    log_event(
        "notifications.sent",
        account_id=account_id,
        decision=decision,
        notification_count=len(state.get("notifications_sent", [])),
    )
    
    return state


def provision_account(state: AgentState) -> AgentState:
    """Provision the customer account in the SaaS platform."""
    account_id = state.get("account_id")
    correlation_id = state.get("correlation_id", "")
    
    # Only provision if decision is PROCEED
    if state.get("decision") != "PROCEED":
        log_event(
            "provisioning.skipped",
            account_id=account_id,
            reason=f"Decision is {state.get('decision')}, not PROCEED",
        )
        return state
    
    log_state_transition(
        from_stage=state.get("stage"),
        to_stage="provisioning",
        account_id=account_id,
        correlation_id=correlation_id,
    )
    state["stage"] = "provisioning"
    
    # Determine tier from contract/opportunity
    clm_data = state.get("clm", {})
    tier = clm_data.get("key_terms", {}).get("sla_tier", "Starter")
    
    # Provision the account
    prov_result = provisioning.provision_account(account_id, tier)
    state["provisioning"] = prov_result
    
    record_action(state, "provision", {
        "tenant_id": prov_result.get("tenant_id"),
        "tier": tier,
        "status": prov_result.get("status"),
    })
    
    state["stage"] = "provisioned"
    
    log_event(
        "provisioning.complete",
        account_id=account_id,
        tenant_id=prov_result.get("tenant_id"),
        tier=tier,
    )
    
    # Send success notifications
    account = state.get("account") or {}
    account_name = account.get("Name", account_id)
    
    notifier.notify_cs_team_success(
        account_name=account_name,
        account_id=account_id,
        tenant_id=prov_result.get("tenant_id"),
        correlation_id=correlation_id,
    )
    record_notification(
        state, "slack", "#cs-onboarding",
        f"Success notification sent for {account_name}"
    )
    
    # Send customer welcome email
    user = state.get("user", {})
    if user.get("Email"):
        notifier.send_customer_welcome_email(
            customer_email=user.get("Email"),
            customer_name=user.get("FirstName", "Customer"),
            account_name=account_name,
            tenant_id=prov_result.get("tenant_id"),
            account_id=account_id,
            correlation_id=correlation_id,
        )
        record_notification(
            state, "email", user.get("Email"),
            f"Welcome email sent to {user.get('Email')}"
        )
    
    return state


def generate_summary_node(state: AgentState) -> AgentState:
    """Generate final human-readable summary."""
    account_id = state.get("account_id")
    
    log_state_transition(
        from_stage=state.get("stage"),
        to_stage="generating_summary",
        account_id=account_id,
        correlation_id=state.get("correlation_id"),
    )
    
    state["human_summary"] = generate_summary(state)
    state["stage"] = "complete"
    
    log_event(
        "onboarding.complete",
        account_id=account_id,
        final_decision=state.get("decision"),
        final_stage=state.get("stage"),
    )
    
    return state

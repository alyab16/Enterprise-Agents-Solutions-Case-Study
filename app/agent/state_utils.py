from typing import Optional, Dict, Any
from datetime import datetime
import uuid
from .state import AgentState, APIErrorInfo
from app.logging.logger import log_event

# Error resolution guides
ERROR_RESOLUTIONS = {
    # Authentication errors
    "authentication": {
        "salesforce": {
            "description": "Salesforce session has expired or credentials are invalid",
            "resolution": "Re-authenticate with Salesforce. Check that the Connected App credentials are valid and the refresh token hasn't expired. Contact your Salesforce admin if the issue persists.",
            "owner": "Integration Admin"
        },
        "netsuite": {
            "description": "NetSuite token-based authentication failed",
            "resolution": "Verify the Token ID and Token Secret in your NetSuite integration settings. Ensure the integration record is active and the role has proper permissions.",
            "owner": "Integration Admin"
        },
        "clm": {
            "description": "CLM API key is invalid or expired",
            "resolution": "Generate a new API key in the CLM admin console. Update the integration configuration with the new credentials.",
            "owner": "Integration Admin"
        },
    },
    # Authorization errors
    "authorization": {
        "salesforce": {
            "description": "User lacks permission to access Salesforce objects",
            "resolution": "Check the integration user's profile and permission sets. Ensure they have Read access to Account, Opportunity, Contract, and User objects.",
            "owner": "Salesforce Admin"
        },
        "netsuite": {
            "description": "User lacks permission to access NetSuite records",
            "resolution": "Verify the role assigned to the integration has the 'Invoice' permission. Check Lists > Employees > Integration User > Access tab.",
            "owner": "NetSuite Admin"
        },
        "clm": {
            "description": "User lacks permission to access contracts in CLM",
            "resolution": "Assign the 'Contract Reader' or 'Contract Administrator' role to the integration user in CLM.",
            "owner": "CLM Admin"
        },
    },
    # Server errors
    "server": {
        "salesforce": {
            "description": "Salesforce service is temporarily unavailable",
            "resolution": "This is typically a temporary issue. Check status.salesforce.com for any ongoing incidents. Retry the operation in a few minutes.",
            "owner": "Support Team"
        },
        "netsuite": {
            "description": "NetSuite server encountered an error",
            "resolution": "Check system.netsuite.com/status for service health. If the issue persists, contact NetSuite support with the error details.",
            "owner": "Support Team"
        },
        "clm": {
            "description": "CLM service is experiencing issues",
            "resolution": "Check the CLM status page for any incidents. Retry the operation after a few minutes. Contact CLM support if the issue persists.",
            "owner": "Support Team"
        },
    },
    # Validation errors
    "validation": {
        "salesforce": {
            "description": "Data validation failed in Salesforce",
            "resolution": "Review the field values being sent. Check for required fields, picklist values, and data format requirements.",
            "owner": "Data Admin"
        },
        "netsuite": {
            "description": "Invalid field value in NetSuite request",
            "resolution": "Check the field values against NetSuite's validation rules. Ensure all required fields are provided and values match expected formats.",
            "owner": "Data Admin"
        },
        "clm": {
            "description": "Contract data validation failed",
            "resolution": "Verify all required contract fields are populated correctly. Check date formats and signatory information.",
            "owner": "Data Admin"
        },
    },
    # Rate limit errors
    "rate_limit": {
        "salesforce": {
            "description": "Salesforce API rate limit exceeded",
            "resolution": "The daily API limit has been reached. Wait until the limit resets (usually 24 hours) or contact Salesforce to increase your API allocation.",
            "owner": "Integration Admin"
        },
        "netsuite": {
            "description": "NetSuite concurrency limit exceeded",
            "resolution": "Too many simultaneous requests. Implement request queuing or reduce the number of concurrent API calls.",
            "owner": "Integration Admin"
        },
        "clm": {
            "description": "CLM API rate limit exceeded",
            "resolution": "Reduce the frequency of API calls. Implement exponential backoff for retries.",
            "owner": "Integration Admin"
        },
    },
}


def get_error_resolution(error_type: str, system: str) -> Dict[str, str]:
    """Get resolution guidance for a specific error type and system."""
    system_resolutions = ERROR_RESOLUTIONS.get(error_type, {})
    return system_resolutions.get(system, {
        "description": f"An error occurred in {system}",
        "resolution": f"Check the {system} integration configuration and logs for more details.",
        "owner": "Support Team"
    })


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
        clm=None,
        provisioning=None,
        api_errors=[],  # Track API errors
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

def add_api_error(
    state: AgentState,
    system: str,
    error_type: str,
    error_code: str,
    message: str,
    http_status: int = 0,
    details: Dict[str, Any] = None,
) -> None:
    """
    Record an API error with full context and resolution guidance.

    Fix A:
      - attach correlation_id, stage, account_id
      - attach entity_context (account/opportunity/contract/user/invoice/clm IDs if present)
      - attach unique error_id
      - keep raw message visible in downstream reports
    """
    if state.get("api_errors") is None:
        state["api_errors"] = []

    # Resolution guidance (templated)
    resolution_info = get_error_resolution(error_type, system)

    error_id = uuid.uuid4().hex[:12]
    correlation_id = state.get("correlation_id", "")
    stage = state.get("stage", "")
    account_id = state.get("account_id", "")

    # Safely grab IDs from whatever we have in state (if present)
    def _safe_get_id(obj: Any, key: str = "Id") -> str:
        return obj.get(key) if isinstance(obj, dict) else ""

    entity_context = {
        "salesforce_account_id": _safe_get_id(state.get("account")),
        "opportunity_id": _safe_get_id(state.get("opportunity")),
        "contract_id": _safe_get_id(state.get("contract")),
        "user_id": _safe_get_id(state.get("user")),
        # Some integrations may use different keys; include best-effort alternatives:
        "netsuite_invoice_id": _safe_get_id(state.get("invoice"), "invoice_id") or _safe_get_id(state.get("invoice"), "Id"),
        "clm_contract_id": _safe_get_id(state.get("clm"), "contract_id") or _safe_get_id(state.get("clm"), "Id"),
    }

    # Enrich details (without overwriting caller-provided fields)
    enriched_details = dict(details or {})
    enriched_details.setdefault("operation", enriched_details.get("operation") or "unknown")
    enriched_details.setdefault("request_id", enriched_details.get("request_id") or "")
    enriched_details.setdefault("account_id", account_id)
    enriched_details.setdefault("correlation_id", correlation_id)
    enriched_details.setdefault("stage", stage)
    enriched_details.setdefault("error_id", error_id)
    enriched_details.setdefault("entity_context", entity_context)

    error_info: APIErrorInfo = {
        "system": system,
        "error_type": error_type,
        "error_code": error_code,
        "message": message,  # <- RAW message preserved (this fixes “generic”)
        "http_status": http_status,
        "timestamp": datetime.utcnow().isoformat(),
        "details": enriched_details,
        "resolution": resolution_info.get("resolution", ""),
        "description": resolution_info.get("description", ""),
        "owner": resolution_info.get("owner", "Support Team"),
        "error_id": error_id,
        "correlation_id": correlation_id,
        "stage": stage,
        "account_id": account_id,
        "entity_context": entity_context,
    }

    state["api_errors"].append(error_info)

    # Log a structured event (helps you debug runs outside the report)
    log_event(
        "api_error.recorded",
        account_id=account_id,
        correlation_id=correlation_id,
        stage=stage,
        system=system,
        error_type=error_type,
        error_code=error_code,
        http_status=http_status,
        error_id=error_id,
        operation=enriched_details.get("operation"),
        request_id=enriched_details.get("request_id"),
        entity_context=entity_context,
    )

    # Make the violation non-generic too (include operation + raw message)
    op = enriched_details.get("operation", "unknown")
    violation_msg = f"{system.upper()} API Error [{error_code}] during {op}: {message}"
    add_violation(state, "api_error", violation_msg)



def has_api_errors(state: AgentState) -> bool:
    """Returns True if any API errors were recorded."""
    return len(state.get("api_errors", [])) > 0


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
        "message": message,
        "type": channel,  # For compatibility
    })

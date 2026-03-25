"""
Rule-based risk analysis fallback.

In the new Pydantic AI architecture, the agent itself performs risk analysis
as part of its reasoning. This module provides a rule-based fallback for
the debug endpoint and report generation when the agent is not involved.
"""

import json
from typing import Dict, List, Any, Optional


def _rule_based_analyze(state: dict) -> dict:
    """
    Rule-based risk analysis.

    Used by the debug endpoint for testing validation logic without
    invoking the full agent.
    """
    violations = state.get("violations", {})
    warnings = state.get("warnings", {})
    api_errors = state.get("api_errors", [])

    violation_count = sum(len(msgs) for msgs in violations.values())
    warning_count = sum(len(msgs) for msgs in warnings.values())
    api_error_count = len(api_errors)

    # Determine risk level
    if api_error_count > 0:
        risk_level = "critical"
    elif violation_count > 0:
        risk_level = "critical" if violation_count > 2 else "high"
    elif warning_count > 3:
        risk_level = "medium"
    elif warning_count > 0:
        risk_level = "low"
    else:
        risk_level = "low"

    # Build risks list
    risks = []

    for error in api_errors:
        system = error.get("system", "api")
        error_type = error.get("error_type", "unknown")
        message = error.get("message", "API error occurred")
        risks.append({
            "issue": f"{system.title()} API {error_type.replace('_', ' ').title()} Error: {message}",
            "impact": f"Cannot fetch required data from {system.title()} - onboarding blocked",
            "urgency": "critical"
        })

    if "account" in violations:
        risks.append({
            "issue": "Account data is missing or invalid",
            "impact": "Cannot identify the customer or their requirements",
            "urgency": "high"
        })

    if "contract" in violations:
        risks.append({
            "issue": "Contract issues detected",
            "impact": "Legal agreement not in place - cannot proceed with provisioning",
            "urgency": "high"
        })

    if "opportunity" in violations:
        risks.append({
            "issue": "Opportunity not in Closed Won status",
            "impact": "Deal may not be finalized - premature onboarding risk",
            "urgency": "high"
        })

    if "invoice" in warnings:
        invoice = state.get("invoice") or {}
        if invoice.get("status") == "OVERDUE":
            risks.append({
                "issue": "Invoice is overdue",
                "impact": "Payment not received - may need finance escalation",
                "urgency": "high"
            })

    # Build recommended actions
    recommended_actions = []
    priority = 1

    for error in api_errors:
        system = error.get("system", "api")
        error_type = error.get("error_type", "unknown")
        if error_type == "authentication":
            recommended_actions.append({
                "action": f"Re-authenticate with {system.title()}",
                "owner": "IT/DevOps",
                "priority": priority
            })
        elif error_type == "authorization":
            recommended_actions.append({
                "action": f"Check {system.title()} API permissions",
                "owner": "IT/DevOps",
                "priority": priority
            })
        else:
            recommended_actions.append({
                "action": f"Investigate {system.title()} API error and retry",
                "owner": "IT/DevOps",
                "priority": priority
            })
        priority += 1

    if "account" in violations:
        recommended_actions.append({
            "action": "Verify account exists in Salesforce and has required fields",
            "owner": "Sales Operations",
            "priority": priority
        })
        priority += 1

    if "contract" in violations or "contract" in warnings:
        recommended_actions.append({
            "action": "Review contract status and expedite signature if needed",
            "owner": "Legal/CS",
            "priority": priority
        })
        priority += 1

    if not recommended_actions and warning_count > 0:
        recommended_actions.append({
            "action": "Review warnings and confirm acceptable to proceed",
            "owner": "Customer Success",
            "priority": 1
        })

    if violation_count == 0 and warning_count == 0 and api_error_count == 0:
        recommended_actions.append({
            "action": "Proceed with automated provisioning",
            "owner": "System",
            "priority": 1
        })

    # Build summary
    account = state.get("account") or {}
    account_name = account.get("Name", "Unknown Account")

    if api_error_count > 0:
        summary = f"Onboarding for {account_name} is BLOCKED due to {api_error_count} API error(s)."
    elif violation_count > 0:
        summary = f"Onboarding for {account_name} is BLOCKED due to {violation_count} critical issue(s)."
    elif warning_count > 0:
        summary = f"Onboarding for {account_name} can proceed with caution. {warning_count} warning(s) identified."
    else:
        summary = f"Onboarding for {account_name} is ready to proceed. All checks passed."

    return {
        "summary": summary,
        "risk_level": risk_level,
        "risks": risks,
        "recommended_actions": recommended_actions,
        "estimated_resolution_time": _estimate_resolution_time(violations, warnings, api_errors),
        "can_proceed_with_warnings": violation_count == 0 and api_error_count == 0
    }


def _estimate_resolution_time(violations: dict, warnings: dict, api_errors: list = None) -> str:
    api_errors = api_errors or []
    violation_count = sum(len(msgs) for msgs in violations.values())
    warning_count = sum(len(msgs) for msgs in warnings.values())
    api_error_count = len(api_errors)

    if api_error_count > 0:
        return "Variable - depends on API issue resolution"
    elif violation_count == 0 and warning_count == 0:
        return "Immediate - ready to provision"
    elif violation_count == 0:
        return "< 1 hour if warnings acceptable"
    elif violation_count <= 2:
        return "1-4 hours depending on issue complexity"
    else:
        return "4-24 hours - multiple critical issues"


def generate_summary(state: dict) -> str:
    """Generate a human-readable summary from state."""
    risk_analysis = state.get("risk_analysis", {})
    if risk_analysis:
        return risk_analysis.get("summary", _fallback_summary(state))
    return _fallback_summary(state)


def _fallback_summary(state: dict) -> str:
    account = state.get("account") or {}
    account_name = account.get("Name", state.get("account_id", "Unknown"))
    decision = state.get("decision", "PENDING")

    violations = state.get("violations", {})
    warnings = state.get("warnings", {})
    api_errors = state.get("api_errors", [])

    violation_count = sum(len(msgs) for msgs in violations.values())
    warning_count = sum(len(msgs) for msgs in warnings.values())
    api_error_count = len(api_errors)

    lines = [
        f"Onboarding Status for {account_name}",
        f"Decision: {decision}",
        f"Violations: {violation_count}",
        f"Warnings: {warning_count}",
        f"API Errors: {api_error_count}",
    ]

    return "\n".join(lines)

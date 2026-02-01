#!/usr/bin/env python3
"""
Standalone Demo Script - Works without LangGraph dependencies
This shows the core logic flow without requiring external packages.

Run with: python demo_standalone.py
"""

import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional

# ============================================================================
# MOCK DATA (Same as in integrations/)
# ============================================================================

MOCK_ACCOUNTS = {
    "ACME-001": {
        "Id": "0018Z00003ACMEQ",
        "Name": "ACME Corp",
        "BillingCountry": "United States",
        "Industry": "Technology",
        "OwnerId": "0058Z000001OWNER",
        "IsDeleted": False,
    },
    "BETA-002": {
        "Id": "0018Z00003BETAQ",
        "Name": "Beta Industries",
        "BillingCountry": "Canada",
        "Industry": "Manufacturing",
        "OwnerId": "0058Z000001OWNER",
        "IsDeleted": False,
    },
    "GAMMA-003": {
        "Id": "0018Z00003GAMMAQ",
        "Name": "Gamma Startup",
        "Industry": "Fintech",
        "OwnerId": "0058Z000001OWNER",
        "IsDeleted": False,
        # Missing BillingCountry
    },
    "DELETED-004": {
        "Id": "0018Z00003DELTAQ",
        "Name": "Deleted Corp",
        "IsDeleted": True,
    },
}

MOCK_USERS = {
    "0058Z000001OWNER": {
        "Id": "0058Z000001OWNER",
        "Username": "cs.manager@stackadapt.demo",
        "Email": "cs.manager@stackadapt.demo",
        "FirstName": "Sarah",
        "LastName": "Johnson",
        "IsActive": True,
        "ProfileId": "00e8Z000001PROFILE",
    },
}

MOCK_OPPORTUNITIES = {
    "ACME-001": {
        "Id": "OPP-ACME",
        "StageName": "Closed Won",
        "Amount": 150000.00,
        "AccountId": "0018Z00003ACMEQ",
        "CloseDate": "2024-01-15",
    },
    "BETA-002": {
        "Id": "OPP-BETA",
        "StageName": "Negotiation",  # Not won
        "Amount": 75000.00,
        "AccountId": "0018Z00003BETAQ",
    },
    "GAMMA-003": {
        "Id": "OPP-GAMMA",
        "StageName": "Closed Won",
        "Amount": 25000.00,
        "AccountId": "0018Z00003GAMMAQ",
    },
}

MOCK_CONTRACTS = {
    "ACME-001": {
        "Id": "CTR-ACME",
        "Status": "Activated",
        "AccountId": "0018Z00003ACMEQ",
        "OwnerId": "0058Z000001OWNER",
        "StartDate": "2024-01-01",
        "ActivatedDate": "2024-01-01",
        "CustomerSignedDate": "2023-12-20",
    },
    "BETA-002": {
        "Id": "CTR-BETA",
        "Status": "Draft",
        "AccountId": "0018Z00003BETAQ",
        "StartDate": "2024-02-01",
    },
    "GAMMA-003": {
        "Id": "CTR-GAMMA",
        "Status": "Activated",
        "AccountId": "0018Z00003GAMMAQ",
        "StartDate": "2024-01-20",
        "ActivatedDate": "2024-01-20",
    },
}

MOCK_INVOICES = {
    "ACME-001": {"invoice_id": "INV-001", "status": "PAID", "amount": 150000.00},
    "BETA-002": {"invoice_id": "INV-002", "status": "PENDING", "amount": 75000.00},
    "GAMMA-003": {"invoice_id": "INV-003", "status": "OVERDUE", "amount": 25000.00, "days_overdue": 25},
}


# ============================================================================
# COLORS FOR TERMINAL OUTPUT
# ============================================================================

class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'


# ============================================================================
# STATE AND INVARIANTS
# ============================================================================

def init_state(account_id: str) -> Dict[str, Any]:
    """Initialize agent state."""
    return {
        "account_id": account_id,
        "correlation_id": str(uuid.uuid4())[:8],
        "violations": {},
        "warnings": {},
        "actions_taken": [],
        "notifications_sent": [],
        "stage": "initialized",
        "decision": "PENDING",
    }


def add_violation(state: dict, domain: str, message: str):
    state.setdefault("violations", {}).setdefault(domain, []).append(message)


def add_warning(state: dict, domain: str, message: str):
    state.setdefault("warnings", {}).setdefault(domain, []).append(message)


def check_account(state: dict, account: Optional[dict]):
    if not account:
        add_violation(state, "account", "Account data missing")
        return
    if not account.get("Id"):
        add_violation(state, "account", "Account.Id is required")
    if not account.get("Name"):
        add_violation(state, "account", "Account.Name is required")
    if account.get("IsDeleted"):
        add_violation(state, "account", "Account is marked as deleted")
    if not account.get("BillingCountry"):
        add_warning(state, "account", "BillingCountry missing")


def check_opportunity(state: dict, opportunity: Optional[dict]):
    if not opportunity:
        add_violation(state, "opportunity", "Opportunity data missing")
        return
    stage = opportunity.get("StageName")
    if stage != "Closed Won":
        add_violation(state, "opportunity", f"Opportunity not won (stage: {stage})")
    if not opportunity.get("Amount"):
        add_warning(state, "opportunity", "Opportunity has no Amount")


def check_contract(state: dict, contract: Optional[dict]):
    if not contract:
        add_violation(state, "contract", "Contract data missing")
        return
    status = contract.get("Status")
    if status not in ["Draft", "In Approval Process", "Activated"]:
        add_violation(state, "contract", f"Invalid contract status: {status}")
    if status == "Draft":
        add_warning(state, "contract", "Contract still in Draft status")
    if status == "Activated" and not contract.get("ActivatedDate"):
        add_violation(state, "contract", "Activated contract missing ActivatedDate")
    if not contract.get("OwnerId"):
        add_warning(state, "contract", "Contract has no owner")


def check_invoice(state: dict, invoice: Optional[dict]):
    if not invoice:
        add_warning(state, "invoice", "Invoice not found")
        return
    status = invoice.get("status")
    if status == "OVERDUE":
        add_warning(state, "invoice", f"Invoice is OVERDUE ({invoice.get('days_overdue', '?')} days)")
    elif status == "PENDING":
        add_warning(state, "invoice", "Invoice pending payment")


# ============================================================================
# RISK ANALYSIS (Rule-based - no LLM required)
# ============================================================================

def analyze_risks(state: dict) -> dict:
    """Generate risk analysis without LLM."""
    violations = state.get("violations", {})
    warnings = state.get("warnings", {})
    api_errors = state.get("api_errors", [])
    
    v_count = sum(len(v) for v in violations.values())
    w_count = sum(len(v) for v in warnings.values())
    api_error_count = len(api_errors)
    
    # Determine risk level - API errors are critical
    if api_error_count > 0:
        risk_level = "critical"
    elif v_count > 2:
        risk_level = "critical"
    elif v_count > 0:
        risk_level = "high"
    elif w_count > 2:
        risk_level = "medium"
    elif w_count > 0:
        risk_level = "low"
    else:
        risk_level = "low"
    
    # Build recommendations
    recommendations = []
    
    # API error recommendations
    if api_error_count > 0:
        for error in api_errors:
            system = error.get("system", "api")
            error_type = error.get("error_type", "unknown")
            if error_type == "authentication":
                recommendations.append({"action": f"Re-authenticate with {system.title()}", "owner": "IT/DevOps"})
            elif error_type == "authorization":
                recommendations.append({"action": f"Check {system.title()} API permissions", "owner": "IT/DevOps"})
            elif error_type in ("server", "rate_limit"):
                recommendations.append({"action": f"Retry {system.title()} API call later", "owner": "System"})
            else:
                recommendations.append({"action": f"Investigate {system.title()} API error", "owner": "IT/DevOps"})
    
    if "account" in violations:
        recommendations.append({"action": "Verify account in Salesforce", "owner": "Sales Ops"})
    if "opportunity" in violations:
        recommendations.append({"action": "Confirm deal is closed-won", "owner": "Sales"})
    if "contract" in violations or "contract" in warnings:
        recommendations.append({"action": "Review contract status", "owner": "Legal/CS"})
    if "invoice" in warnings:
        recommendations.append({"action": "Follow up on payment", "owner": "Finance"})
    
    if not recommendations and v_count == 0 and api_error_count == 0:
        recommendations.append({"action": "Proceed with provisioning", "owner": "System"})
    
    # Summary
    account = state.get("account") or {}
    account_name = account.get("Name", state.get("account_id"))
    if api_error_count > 0:
        summary = f"Onboarding for {account_name} is BLOCKED due to {api_error_count} API error(s)"
    elif v_count > 0:
        summary = f"Onboarding for {account_name} is BLOCKED due to {v_count} critical issue(s)"
    elif w_count > 0:
        summary = f"Onboarding for {account_name} can proceed with caution ({w_count} warning(s))"
    else:
        summary = f"Onboarding for {account_name} is ready to proceed"
    
    return {
        "summary": summary,
        "risk_level": risk_level,
        "recommended_actions": recommendations,
        "can_proceed": v_count == 0 and api_error_count == 0,
    }


# ============================================================================
# NOTIFICATIONS (Mock)
# ============================================================================

def send_notification(state: dict, channel: str, message_type: str):
    """Record a notification."""
    state["notifications_sent"].append({
        "channel": channel,
        "type": message_type,
        "time": datetime.now().isoformat(),
    })


# ============================================================================
# MAIN WORKFLOW
# ============================================================================

def run_onboarding(account_id: str) -> dict:
    """Run the full onboarding workflow."""
    
    # Initialize
    state = init_state(account_id)
    
    # Fetch data
    state["account"] = MOCK_ACCOUNTS.get(account_id)
    state["opportunity"] = MOCK_OPPORTUNITIES.get(account_id)
    state["contract"] = MOCK_CONTRACTS.get(account_id)
    state["invoice"] = MOCK_INVOICES.get(account_id)
    
    if state["account"]:
        owner_id = state["account"].get("OwnerId")
        state["user"] = MOCK_USERS.get(owner_id)
    
    # Run validations
    check_account(state, state.get("account"))
    check_opportunity(state, state.get("opportunity"))
    check_contract(state, state.get("contract"))
    check_invoice(state, state.get("invoice"))
    
    # Analyze risks
    state["risk_analysis"] = analyze_risks(state)
    
    # Make decision
    v_count = sum(len(v) for v in state.get("violations", {}).values())
    w_count = sum(len(v) for v in state.get("warnings", {}).values())
    
    if v_count > 0:
        state["decision"] = "BLOCK"
        state["stage"] = "blocked"
        send_notification(state, "#cs-onboarding-alerts", "blocked")
    elif w_count > 0:
        state["decision"] = "ESCALATE"
        state["stage"] = "escalation_required"
        send_notification(state, "#cs-onboarding", "escalation")
    else:
        state["decision"] = "PROCEED"
        state["stage"] = "provisioned"
        state["provisioning"] = {
            "tenant_id": f"TEN-{uuid.uuid4().hex[:8].upper()}",
            "status": "ACTIVE",
        }
        state["actions_taken"].append({"type": "provision", "tenant_id": state["provisioning"]["tenant_id"]})
        send_notification(state, "#cs-onboarding", "success")
        send_notification(state, "customer@email.com", "welcome_email")
    
    return state


# ============================================================================
# DISPLAY FUNCTIONS
# ============================================================================

def print_header(text: str):
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'=' * 70}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.CYAN}{text.center(70)}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'=' * 70}{Colors.ENDC}\n")


def print_section(title: str):
    print(f"\n{Colors.BOLD}{Colors.BLUE}▶ {title}{Colors.ENDC}")
    print(f"{Colors.DIM}{'-' * 50}{Colors.ENDC}")


def print_decision(decision: str):
    colors = {"PROCEED": Colors.GREEN, "ESCALATE": Colors.YELLOW, "BLOCK": Colors.RED}
    emojis = {"PROCEED": "✅", "ESCALATE": "⚠️", "BLOCK": "🚫"}
    c = colors.get(decision, Colors.ENDC)
    e = emojis.get(decision, "?")
    print(f"\n{Colors.BOLD}Decision: {c}{e} {decision}{Colors.ENDC}")


def display_result(result: dict):
    """Display a single scenario result."""
    
    account = result.get("account") or {}
    account_name = account.get("Name", result.get("account_id"))
    
    print(f"{Colors.DIM}Account: {account_name} ({result.get('account_id')}){Colors.ENDC}")
    
    print_decision(result.get("decision"))
    
    risk = result.get("risk_analysis", {})
    print(f"Risk Level: {risk.get('risk_level', 'N/A').upper()}")
    
    print_section("Summary")
    print(f"  {risk.get('summary', 'No summary')}")
    
    print_section("Violations (Blocking)")
    violations = result.get("violations", {})
    if violations and any(violations.values()):
        for domain, msgs in violations.items():
            for msg in msgs:
                print(f"  {Colors.RED}✗ [{domain}]{Colors.ENDC} {msg}")
    else:
        print(f"  {Colors.GREEN}None{Colors.ENDC}")
    
    print_section("Warnings")
    warnings = result.get("warnings", {})
    if warnings and any(warnings.values()):
        for domain, msgs in warnings.items():
            for msg in msgs:
                print(f"  {Colors.YELLOW}⚠ [{domain}]{Colors.ENDC} {msg}")
    else:
        print(f"  {Colors.GREEN}None{Colors.ENDC}")
    
    print_section("Recommended Actions")
    for i, rec in enumerate(risk.get("recommended_actions", []), 1):
        owner = rec.get("owner", "")
        print(f"  {i}. {rec.get('action')} ({Colors.CYAN}{owner}{Colors.ENDC})")
    
    print_section("Notifications Sent")
    for notif in result.get("notifications_sent", []):
        emoji = "💬" if notif.get("channel", "").startswith("#") else "📧"
        print(f"  {emoji} {notif.get('type')} → {notif.get('channel')}")
    
    if result.get("provisioning"):
        print_section("Provisioning")
        prov = result.get("provisioning")
        print(f"  {Colors.GREEN}✓ Tenant ID:{Colors.ENDC} {prov.get('tenant_id')}")
        print(f"  {Colors.GREEN}✓ Status:{Colors.ENDC} {prov.get('status')}")


# ============================================================================
# MAIN
# ============================================================================

def main():
    scenarios = [
        ("ACME-001", "Happy Path - Full Success", "All checks pass, account provisioned"),
        ("BETA-002", "Blocked - Opportunity Not Won", "Opportunity in negotiation stage"),
        ("GAMMA-003", "Escalation - Overdue Invoice", "Invoice overdue, needs finance review"),
        ("DELETED-004", "Blocked - Deleted Account", "Account marked as deleted"),
        ("MISSING-999", "Blocked - Account Not Found", "Account does not exist"),
    ]
    
    print_header("Enterprise Onboarding Agent Demo")
    print(f"{Colors.DIM}Demonstrating AI-powered onboarding automation{Colors.ENDC}")
    print(f"{Colors.DIM}Timestamp: {datetime.now().isoformat()}{Colors.ENDC}")
    
    results = []
    
    for account_id, name, desc in scenarios:
        print_header(f"Scenario: {name}")
        print(f"{Colors.DIM}{desc}{Colors.ENDC}")
        
        result = run_onboarding(account_id)
        display_result(result)
        
        results.append({
            "id": account_id,
            "name": name,
            "decision": result.get("decision"),
            "risk_level": result.get("risk_analysis", {}).get("risk_level"),
        })
        
        print(f"\n{Colors.DIM}{'─' * 70}{Colors.ENDC}")
    
    # Summary
    print_header("Summary of All Scenarios")
    print(f"{'Account':<15} {'Scenario':<30} {'Decision':<12} {'Risk':<10}")
    print(f"{'-' * 15} {'-' * 30} {'-' * 12} {'-' * 10}")
    
    for r in results:
        colors = {"PROCEED": Colors.GREEN, "ESCALATE": Colors.YELLOW, "BLOCK": Colors.RED}
        c = colors.get(r["decision"], Colors.ENDC)
        print(f"{r['id']:<15} {r['name'][:30]:<30} {c}{r['decision']:<12}{Colors.ENDC} {r.get('risk_level', 'N/A'):<10}")
    
    print()


if __name__ == "__main__":
    main()

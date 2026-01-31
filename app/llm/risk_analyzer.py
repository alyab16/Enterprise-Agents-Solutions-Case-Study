"""
LLM-powered risk analysis for onboarding.
Generates human-readable explanations and recommended actions.
"""

import json
import os
from typing import Optional
from app.logging.logger import log_event

# Try to import OpenAI, but handle gracefully if not available
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    OpenAI = None


RISK_ANALYSIS_SYSTEM_PROMPT = """You are an AI assistant helping Customer Success teams understand onboarding issues.

Your job is to analyze the current state of a customer onboarding and provide:
1. A clear, human-readable summary of the situation
2. Identification of risks and their business impact
3. Specific, actionable recommendations

Be concise but thorough. Use business language, not technical jargon.
Format your response as JSON with the following structure:
{
    "summary": "Brief 1-2 sentence overview of the onboarding status",
    "risk_level": "low|medium|high|critical",
    "risks": [
        {
            "issue": "What the problem is",
            "impact": "Business impact of this issue",
            "urgency": "low|medium|high"
        }
    ],
    "recommended_actions": [
        {
            "action": "Specific action to take",
            "owner": "Who should do this (CS, Finance, Legal, etc.)",
            "priority": 1
        }
    ],
    "estimated_resolution_time": "Time estimate to resolve all issues",
    "can_proceed_with_warnings": true/false
}"""


def analyze_risks(state: dict) -> dict:
    """
    Use LLM to analyze the current onboarding state and generate
    human-readable risk assessment and recommendations.
    """
    # Build context for the LLM
    context = _build_analysis_context(state)
    
    # Try LLM analysis first
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key and OPENAI_AVAILABLE:
        try:
            return _llm_analyze(context, state)
        except Exception as e:
            log_event("llm.risk_analysis.error", error=str(e))
    
    # Fallback to rule-based analysis
    return _rule_based_analyze(state)


def _build_analysis_context(state: dict) -> str:
    """Build a context string for the LLM."""
    
    sections = []
    
    # Account info
    account = state.get("account")
    if account:
        sections.append(f"""ACCOUNT:
        - Name: {account.get('Name', 'Unknown')}
        - Industry: {account.get('Industry', 'Not specified')}
        - Country: {account.get('BillingCountry', 'Not specified')}""")
    else:
        sections.append("ACCOUNT: Missing")
    
    # Opportunity info
    opportunity = state.get("opportunity")
    if opportunity:
        sections.append(f"""OPPORTUNITY:
        - Stage: {opportunity.get('StageName', 'Unknown')}
        - Amount: ${opportunity.get('Amount', 0):,.2f}
        - Close Date: {opportunity.get('CloseDate', 'Unknown')}""")
    else:
        sections.append("OPPORTUNITY: Missing")
    
    # Contract info
    contract = state.get("contract")
    if contract:
        sections.append(f"""CONTRACT:
        - Status: {contract.get('Status', 'Unknown')}
        - Start Date: {contract.get('StartDate', 'Unknown')}
        - Has Owner: {'Yes' if contract.get('OwnerId') else 'No'}""")
    else:
        sections.append("CONTRACT: Missing")
    
    # Invoice info
    invoice = state.get("invoice")
    if invoice:
        sections.append(f"""INVOICE:
        - Status: {invoice.get('status', 'Unknown')}
        - Amount: ${invoice.get('amount', 0):,.2f}
        - Due Date: {invoice.get('due_date', 'Unknown')}""")
    else:
        sections.append("INVOICE: Not found")
    
    # Violations and warnings
    violations = state.get("violations", {})
    warnings = state.get("warnings", {})
    
    if violations:
        violation_list = []
        for domain, msgs in violations.items():
            for msg in msgs:
                violation_list.append(f"- [{domain}] {msg}")
        sections.append(f"""BLOCKING VIOLATIONS:
{chr(10).join(violation_list)}""")
    
    if warnings:
        warning_list = []
        for domain, msgs in warnings.items():
            for msg in msgs:
                warning_list.append(f"- [{domain}] {msg}")
        sections.append(f"""WARNINGS:
{chr(10).join(warning_list)}""")
    
    return "\n\n".join(sections)


def _llm_analyze(context: str, state: dict) -> dict:
    """Use OpenAI to analyze risks."""
    
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    response = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        messages=[
            {"role": "system", "content": RISK_ANALYSIS_SYSTEM_PROMPT},
            {"role": "user", "content": f"Analyze this onboarding state:\n\n{context}"}
        ],
        temperature=0.3,
        response_format={"type": "json_object"},
    )
    
    result = json.loads(response.choices[0].message.content)
    
    log_event(
        "llm.risk_analysis.success",
        account_id=state.get("account_id"),
        risk_level=result.get("risk_level"),
    )
    
    return result


def _rule_based_analyze(state: dict) -> dict:
    """
    Fallback rule-based risk analysis when LLM is unavailable.
    """
    violations = state.get("violations", {})
    warnings = state.get("warnings", {})
    
    # Count issues
    violation_count = sum(len(msgs) for msgs in violations.values())
    warning_count = sum(len(msgs) for msgs in warnings.values())
    
    # Determine risk level
    if violation_count > 0:
        risk_level = "critical" if violation_count > 2 else "high"
    elif warning_count > 3:
        risk_level = "medium"
    elif warning_count > 0:
        risk_level = "low"
    else:
        risk_level = "low"
    
    # Build risks list
    risks = []
    
    # Check for specific patterns
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
        invoice = state.get("invoice", {})
        if invoice.get("status") == "OVERDUE":
            risks.append({
                "issue": "Invoice is overdue",
                "impact": "Payment not received - may need finance escalation",
                "urgency": "high"
            })
        elif invoice.get("status") == "PENDING":
            risks.append({
                "issue": "Invoice pending payment",
                "impact": "Provisioning may need to wait for payment",
                "urgency": "medium"
            })
    
    if "contract" in warnings:
        contract = state.get("contract", {})
        if contract.get("Status") == "Draft":
            risks.append({
                "issue": "Contract still in draft status",
                "impact": "Contract not yet sent for signature",
                "urgency": "medium"
            })
    
    # Build recommended actions
    recommended_actions = []
    priority = 1
    
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
    
    if "invoice" in warnings:
        invoice = state.get("invoice", {})
        if invoice.get("status") in ["OVERDUE", "PENDING"]:
            recommended_actions.append({
                "action": "Follow up on invoice payment status",
                "owner": "Finance",
                "priority": priority
            })
            priority += 1
    
    if not recommended_actions and warning_count > 0:
        recommended_actions.append({
            "action": "Review warnings and confirm acceptable to proceed",
            "owner": "Customer Success",
            "priority": 1
        })
    
    if violation_count == 0 and warning_count == 0:
        recommended_actions.append({
            "action": "Proceed with automated provisioning",
            "owner": "System",
            "priority": 1
        })
    
    # Build summary
    account = state.get("account") or {}
    account_name = account.get("Name", "Unknown Account")
    
    if violation_count > 0:
        summary = f"Onboarding for {account_name} is BLOCKED due to {violation_count} critical issue(s) that must be resolved."
    elif warning_count > 0:
        summary = f"Onboarding for {account_name} can proceed with caution. {warning_count} warning(s) identified for review."
    else:
        summary = f"Onboarding for {account_name} is ready to proceed. All checks passed."
    
    return {
        "summary": summary,
        "risk_level": risk_level,
        "risks": risks,
        "recommended_actions": recommended_actions,
        "estimated_resolution_time": _estimate_resolution_time(violations, warnings),
        "can_proceed_with_warnings": violation_count == 0
    }


def _estimate_resolution_time(violations: dict, warnings: dict) -> str:
    """Estimate time to resolve issues."""
    violation_count = sum(len(msgs) for msgs in violations.values())
    warning_count = sum(len(msgs) for msgs in warnings.values())
    
    if violation_count == 0 and warning_count == 0:
        return "Immediate - ready to provision"
    elif violation_count == 0:
        return "< 1 hour if warnings acceptable"
    elif violation_count <= 2:
        return "1-4 hours depending on issue complexity"
    else:
        return "4-24 hours - multiple critical issues"


def generate_summary(state: dict) -> str:
    """
    Generate a human-readable summary of the onboarding state.
    Uses LLM if available, otherwise falls back to template.
    """
    risk_analysis = state.get("risk_analysis", {})
    
    if risk_analysis:
        return risk_analysis.get("summary", _fallback_summary(state))
    
    return _fallback_summary(state)


def _fallback_summary(state: dict) -> str:
    """Generate a simple template-based summary."""
    account = state.get("account") or {}
    account_name = account.get("Name", state.get("account_id", "Unknown"))
    stage = state.get("stage", "unknown")
    decision = state.get("decision", "PENDING")
    
    violations = state.get("violations", {})
    warnings = state.get("warnings", {})
    
    violation_count = sum(len(msgs) for msgs in violations.values())
    warning_count = sum(len(msgs) for msgs in warnings.values())
    
    lines = [
        f"Onboarding Status for {account_name}",
        f"Stage: {stage}",
        f"Decision: {decision}",
        f"Violations: {violation_count}",
        f"Warnings: {warning_count}",
    ]
    
    actions = state.get("actions_taken", [])
    if actions:
        lines.append(f"Actions Taken: {len(actions)}")
    
    return "\n".join(lines)

"""
Report Generator for Onboarding Agent runs.

Generates:
- HTML email templates (simulated email output)
- Markdown run reports
- JSON audit logs
"""

import os
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

# Output directory for generated reports
REPORTS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "reports_output")
os.makedirs(REPORTS_DIR, exist_ok=True)


# ============================================================================
# HTML EMAIL TEMPLATES
# ============================================================================

def generate_email_html(
    to: str,
    subject: str,
    body_sections: List[Dict[str, Any]],
    footer_text: str = None,
) -> str:
    """
    Generate a professional HTML email template.
    
    Args:
        to: Recipient email
        subject: Email subject
        body_sections: List of sections with 'title' and 'content'
        footer_text: Optional footer text
    
    Returns:
        Complete HTML email as string
    """
    sections_html = ""
    for section in body_sections:
        sections_html += f"""
        <div style="margin-bottom: 20px;">
            <h3 style="color: #333; margin-bottom: 10px; font-size: 16px;">{section.get('title', '')}</h3>
            <div style="color: #555; line-height: 1.6;">{section.get('content', '')}</div>
        </div>
        """
    
    footer = footer_text or "This is an automated message from the Enterprise Onboarding Agent."
    
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{subject}</title>
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f5f5f5;">
    
    <!-- Email Container -->
    <div style="background-color: #ffffff; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); overflow: hidden;">
        
        <!-- Header -->
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center;">
            <h1 style="color: #ffffff; margin: 0; font-size: 24px;">StackAdapt</h1>
            <p style="color: rgba(255,255,255,0.9); margin: 10px 0 0 0; font-size: 14px;">Customer Onboarding</p>
        </div>
        
        <!-- Subject Line -->
        <div style="padding: 20px 30px; border-bottom: 1px solid #eee;">
            <h2 style="color: #333; margin: 0; font-size: 20px;">{subject}</h2>
            <p style="color: #888; margin: 5px 0 0 0; font-size: 12px;">To: {to}</p>
        </div>
        
        <!-- Body -->
        <div style="padding: 30px;">
            {sections_html}
        </div>
        
        <!-- Footer -->
        <div style="background-color: #f9f9f9; padding: 20px 30px; border-top: 1px solid #eee;">
            <p style="color: #888; font-size: 12px; margin: 0; text-align: center;">
                {footer}
            </p>
            <p style="color: #aaa; font-size: 11px; margin: 10px 0 0 0; text-align: center;">
                Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}
            </p>
        </div>
    </div>
    
</body>
</html>"""
    
    return html


def generate_blocked_notification_email(
    account_name: str,
    account_id: str,
    violations: Dict[str, List[str]],
    warnings: Dict[str, List[str]],
    recommended_actions: List[Dict[str, Any]],
    correlation_id: str,
) -> str:
    """Generate HTML email for blocked onboarding notification."""
    
    # Build violations list
    violations_html = "<ul style='margin: 0; padding-left: 20px;'>"
    for domain, msgs in violations.items():
        for msg in msgs:
            violations_html += f"<li style='color: #dc3545; margin: 5px 0;'><strong>{domain}:</strong> {msg}</li>"
    violations_html += "</ul>"
    
    # Build warnings list
    warnings_html = ""
    if warnings and any(warnings.values()):
        warnings_html = "<ul style='margin: 0; padding-left: 20px;'>"
        for domain, msgs in warnings.items():
            for msg in msgs:
                warnings_html += f"<li style='color: #ffc107; margin: 5px 0;'><strong>{domain}:</strong> {msg}</li>"
        warnings_html += "</ul>"
    else:
        warnings_html = "<p style='color: #28a745;'>None</p>"
    
    # Build actions list
    actions_html = "<ol style='margin: 0; padding-left: 20px;'>"
    for action in recommended_actions:
        if isinstance(action, dict):
            actions_html += f"<li style='margin: 5px 0;'>{action.get('action', str(action))} <span style='color: #888;'>({action.get('owner', 'TBD')})</span></li>"
        else:
            actions_html += f"<li style='margin: 5px 0;'>{action}</li>"
    actions_html += "</ol>"
    
    sections = [
        {
            "title": "🚨 Onboarding Status: BLOCKED",
            "content": f"""
                <div style="background-color: #f8d7da; border: 1px solid #f5c6cb; border-radius: 4px; padding: 15px; margin-bottom: 15px;">
                    <p style="margin: 0; color: #721c24;">
                        The onboarding process for <strong>{account_name}</strong> has been blocked due to critical issues that require resolution.
                    </p>
                </div>
            """
        },
        {
            "title": "❌ Critical Violations",
            "content": violations_html
        },
        {
            "title": "⚠️ Warnings",
            "content": warnings_html
        },
        {
            "title": "📋 Recommended Actions",
            "content": actions_html
        },
        {
            "title": "🔗 Quick Links",
            "content": f"""
                <p>
                    <a href="https://crm.example.com/accounts/{account_id}" style="color: #667eea; text-decoration: none;">View in Salesforce</a> |
                    <a href="https://agent.example.com/runs/{correlation_id}" style="color: #667eea; text-decoration: none;">View Agent Run</a>
                </p>
            """
        }
    ]
    
    return generate_email_html(
        to="cs-team@stackadapt.com",
        subject=f"🚨 Onboarding BLOCKED - {account_name}",
        body_sections=sections
    )


def generate_success_notification_email(
    account_name: str,
    account_id: str,
    tenant_id: str,
    tier: str,
    customer_email: str,
    correlation_id: str,
) -> str:
    """Generate HTML email for successful onboarding notification."""
    
    sections = [
        {
            "title": "✅ Onboarding Complete",
            "content": f"""
                <div style="background-color: #d4edda; border: 1px solid #c3e6cb; border-radius: 4px; padding: 15px; margin-bottom: 15px;">
                    <p style="margin: 0; color: #155724;">
                        <strong>{account_name}</strong> has been successfully onboarded and provisioned!
                    </p>
                </div>
            """
        },
        {
            "title": "📦 Provisioning Details",
            "content": f"""
                <table style="width: 100%; border-collapse: collapse;">
                    <tr><td style="padding: 8px 0; border-bottom: 1px solid #eee;"><strong>Tenant ID:</strong></td><td style="padding: 8px 0; border-bottom: 1px solid #eee;"><code style="background: #f4f4f4; padding: 2px 6px; border-radius: 3px;">{tenant_id}</code></td></tr>
                    <tr><td style="padding: 8px 0; border-bottom: 1px solid #eee;"><strong>Tier:</strong></td><td style="padding: 8px 0; border-bottom: 1px solid #eee;">{tier}</td></tr>
                    <tr><td style="padding: 8px 0; border-bottom: 1px solid #eee;"><strong>Status:</strong></td><td style="padding: 8px 0; border-bottom: 1px solid #eee;"><span style="color: #28a745;">Active</span></td></tr>
                </table>
            """
        },
        {
            "title": "📝 Next Steps",
            "content": """
                <ol style="margin: 0; padding-left: 20px;">
                    <li style="margin: 8px 0;">Schedule kickoff call with customer</li>
                    <li style="margin: 8px 0;">Verify customer received welcome email</li>
                    <li style="margin: 8px 0;">Assign dedicated onboarding specialist</li>
                    <li style="margin: 8px 0;">Set up first training session</li>
                </ol>
            """
        },
        {
            "title": "🔗 Quick Links",
            "content": f"""
                <p>
                    <a href="https://app.example.com/admin/{tenant_id}" style="color: #667eea; text-decoration: none;">View Tenant</a> |
                    <a href="https://crm.example.com/accounts/{account_id}" style="color: #667eea; text-decoration: none;">View in Salesforce</a> |
                    <a href="https://agent.example.com/runs/{correlation_id}" style="color: #667eea; text-decoration: none;">View Agent Run</a>
                </p>
            """
        }
    ]
    
    return generate_email_html(
        to="cs-team@stackadapt.com",
        subject=f"✅ Onboarding Complete - {account_name}",
        body_sections=sections
    )


def generate_customer_welcome_email(
    customer_name: str,
    account_name: str,
    tenant_id: str,
    login_url: str,
    cs_manager_name: str,
    cs_manager_email: str,
) -> str:
    """Generate HTML welcome email for the customer."""
    
    sections = [
        {
            "title": f"Welcome to StackAdapt, {customer_name}! 🎉",
            "content": f"""
                <p>We're thrilled to have <strong>{account_name}</strong> join the StackAdapt family!</p>
                <p>Your account has been provisioned and you're ready to start driving results with our programmatic advertising platform.</p>
            """
        },
        {
            "title": "🔐 Your Account Details",
            "content": f"""
                <div style="background-color: #f8f9fa; border-radius: 4px; padding: 15px; margin-bottom: 15px;">
                    <table style="width: 100%;">
                        <tr><td style="padding: 5px 0;"><strong>Login URL:</strong></td><td><a href="{login_url}" style="color: #667eea;">{login_url}</a></td></tr>
                        <tr><td style="padding: 5px 0;"><strong>Tenant ID:</strong></td><td><code style="background: #fff; padding: 2px 6px; border-radius: 3px;">{tenant_id}</code></td></tr>
                    </table>
                </div>
                <p style="color: #888; font-size: 13px;">Use your email address to log in. You'll receive a separate email to set your password.</p>
            """
        },
        {
            "title": "🚀 Getting Started",
            "content": """
                <ol style="margin: 0; padding-left: 20px;">
                    <li style="margin: 10px 0;"><strong>Log in</strong> to your new account using the link above</li>
                    <li style="margin: 10px 0;"><strong>Complete the platform tour</strong> to learn the basics</li>
                    <li style="margin: 10px 0;"><strong>Set up your first campaign</strong> with our guided wizard</li>
                    <li style="margin: 10px 0;"><strong>Explore our resources</strong> in the Help Center</li>
                </ol>
            """
        },
        {
            "title": "👤 Your Customer Success Manager",
            "content": f"""
                <div style="display: flex; align-items: center; background-color: #f8f9fa; border-radius: 4px; padding: 15px;">
                    <div style="width: 50px; height: 50px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 50%; display: flex; align-items: center; justify-content: center; color: white; font-weight: bold; margin-right: 15px;">
                        {cs_manager_name[0]}
                    </div>
                    <div>
                        <p style="margin: 0; font-weight: bold;">{cs_manager_name}</p>
                        <p style="margin: 5px 0 0 0; color: #888;"><a href="mailto:{cs_manager_email}" style="color: #667eea;">{cs_manager_email}</a></p>
                    </div>
                </div>
                <p style="margin-top: 15px;">Your CS Manager will reach out shortly to schedule your kickoff call and answer any questions.</p>
            """
        },
    ]
    
    return generate_email_html(
        to=f"{customer_name.lower().replace(' ', '.')}@{account_name.lower().replace(' ', '')}.com",
        subject=f"Welcome to StackAdapt, {account_name}! 🎉",
        body_sections=sections,
        footer_text="Questions? Reply to this email or contact your Customer Success Manager."
    )


# ============================================================================
# MARKDOWN REPORT GENERATOR
# ============================================================================

def generate_run_report_markdown(
    account_id: str,
    account_name: str,
    correlation_id: str,
    decision: str,
    stage: str,
    risk_analysis: Dict[str, Any],
    violations: Dict[str, List[str]],
    warnings: Dict[str, List[str]],
    actions_taken: List[Dict[str, Any]],
    notifications_sent: List[Dict[str, Any]],
    provisioning: Optional[Dict[str, Any]],
    duration_ms: int = 0,
) -> str:
    """Generate a detailed Markdown report for an onboarding run."""
    
    timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
    
    # Decision emoji
    decision_emoji = {"PROCEED": "✅", "ESCALATE": "⚠️", "BLOCK": "🚫"}.get(decision, "❓")
    
    # Build violations section
    violations_md = ""
    if violations and any(violations.values()):
        for domain, msgs in violations.items():
            for msg in msgs:
                violations_md += f"- **{domain}**: {msg}\n"
    else:
        violations_md = "_None_\n"
    
    # Build warnings section
    warnings_md = ""
    if warnings and any(warnings.values()):
        for domain, msgs in warnings.items():
            for msg in msgs:
                warnings_md += f"- **{domain}**: {msg}\n"
    else:
        warnings_md = "_None_\n"
    
    # Build actions section
    actions_md = ""
    if actions_taken:
        for action in actions_taken:
            actions_md += f"- {action.get('type', 'unknown')}: {json.dumps(action)}\n"
    else:
        actions_md = "_None_\n"
    
    # Build notifications section
    notifications_md = ""
    if notifications_sent:
        for notif in notifications_sent:
            channel = notif.get('channel', notif.get('to', 'unknown'))
            notifications_md += f"- {notif.get('type', 'unknown')} → {channel}\n"
    else:
        notifications_md = "_None_\n"
    
    # Build provisioning section
    provisioning_md = ""
    if provisioning:
        provisioning_md = f"""
| Field | Value |
|-------|-------|
| Tenant ID | `{provisioning.get('tenant_id', 'N/A')}` |
| Status | {provisioning.get('status', 'N/A')} |
| Tier | {provisioning.get('tier', 'N/A')} |
"""
    else:
        provisioning_md = "_Not provisioned_"
    
    # Risk analysis
    risk_level = risk_analysis.get('risk_level', 'N/A').upper()
    summary = risk_analysis.get('summary', 'No summary available')
    
    recommended_actions_md = ""
    for i, action in enumerate(risk_analysis.get('recommended_actions', []), 1):
        if isinstance(action, dict):
            recommended_actions_md += f"{i}. {action.get('action', str(action))} _(Owner: {action.get('owner', 'TBD')})_\n"
        else:
            recommended_actions_md += f"{i}. {action}\n"
    
    if not recommended_actions_md:
        recommended_actions_md = "_None_"
    
    markdown = f"""# Onboarding Run Report

## Summary

| Field | Value |
|-------|-------|
| **Account** | {account_name} (`{account_id}`) |
| **Correlation ID** | `{correlation_id}` |
| **Timestamp** | {timestamp} |
| **Decision** | {decision_emoji} **{decision}** |
| **Final Stage** | {stage} |
| **Risk Level** | {risk_level} |
| **Duration** | {duration_ms}ms |

---

## Risk Analysis

### Summary
{summary}

### Recommended Actions
{recommended_actions_md}

---

## Validation Results

### Critical Violations (Blocking)
{violations_md}

### Warnings (Non-blocking)
{warnings_md}

---

## Actions Taken
{actions_md}

---

## Notifications Sent
{notifications_md}

---

## Provisioning
{provisioning_md}

---

## Audit Information

- **Run ID**: `{correlation_id}`
- **Generated**: {timestamp}
- **Agent Version**: 1.0.0
- **Environment**: Demo

---

_This report was automatically generated by the Enterprise Onboarding Agent._
"""
    
    return markdown


# ============================================================================
# FILE SAVING UTILITIES
# ============================================================================

def save_email_html(filename: str, html_content: str) -> str:
    """Save HTML email to file and return path."""
    filepath = os.path.join(REPORTS_DIR, filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(html_content)
    return filepath


def save_report_markdown(filename: str, markdown_content: str) -> str:
    """Save Markdown report to file and return path."""
    filepath = os.path.join(REPORTS_DIR, filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(markdown_content)
    return filepath


def save_audit_json(filename: str, data: Dict[str, Any]) -> str:
    """Save audit log as JSON and return path."""
    filepath = os.path.join(REPORTS_DIR, filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, default=str)
    return filepath


# ============================================================================
# MAIN REPORT GENERATION FUNCTION
# ============================================================================

def generate_full_run_report(state: Dict[str, Any]) -> Dict[str, str]:
    """
    Generate all reports for an onboarding run.
    
    Returns dict with paths to generated files.
    """
    account_id = state.get("account_id", "unknown")
    account = state.get("account") or {}
    account_name = account.get("Name", account_id)
    correlation_id = state.get("correlation_id", "unknown")
    decision = state.get("decision", "UNKNOWN")
    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    
    generated_files = {}
    
    # Generate Markdown report
    markdown = generate_run_report_markdown(
        account_id=account_id,
        account_name=account_name,
        correlation_id=correlation_id,
        decision=decision,
        stage=state.get("stage", "unknown"),
        risk_analysis=state.get("risk_analysis", {}),
        violations=state.get("violations", {}),
        warnings=state.get("warnings", {}),
        actions_taken=state.get("actions_taken", []),
        notifications_sent=state.get("notifications_sent", []),
        provisioning=state.get("provisioning"),
    )
    generated_files["markdown"] = save_report_markdown(
        f"run_report_{account_id}_{timestamp}.md",
        markdown
    )
    
    # Generate appropriate email based on decision
    if decision == "BLOCK":
        email_html = generate_blocked_notification_email(
            account_name=account_name,
            account_id=account_id,
            violations=state.get("violations", {}),
            warnings=state.get("warnings", {}),
            recommended_actions=state.get("risk_analysis", {}).get("recommended_actions", []),
            correlation_id=correlation_id,
        )
        generated_files["email_html"] = save_email_html(
            f"email_blocked_{account_id}_{timestamp}.html",
            email_html
        )
    
    elif decision == "PROCEED":
        provisioning = state.get("provisioning", {})
        email_html = generate_success_notification_email(
            account_name=account_name,
            account_id=account_id,
            tenant_id=provisioning.get("tenant_id", "N/A"),
            tier=provisioning.get("tier", "N/A"),
            customer_email=account.get("Email", "customer@example.com"),
            correlation_id=correlation_id,
        )
        generated_files["email_html"] = save_email_html(
            f"email_success_{account_id}_{timestamp}.html",
            email_html
        )
        
        # Also generate customer welcome email
        user = state.get("user") or {}
        welcome_html = generate_customer_welcome_email(
            customer_name=user.get("FirstName", "Customer"),
            account_name=account_name,
            tenant_id=provisioning.get("tenant_id", "N/A"),
            login_url="https://app.stackadapt.demo/login",
            cs_manager_name=user.get("Name", "Sarah Johnson"),
            cs_manager_email=user.get("Email", "cs@stackadapt.demo"),
        )
        generated_files["welcome_email_html"] = save_email_html(
            f"email_welcome_{account_id}_{timestamp}.html",
            welcome_html
        )
    
    # Save audit JSON
    audit_data = {
        "correlation_id": correlation_id,
        "account_id": account_id,
        "account_name": account_name,
        "decision": decision,
        "stage": state.get("stage"),
        "timestamp": datetime.utcnow().isoformat(),
        "risk_analysis": state.get("risk_analysis"),
        "violations": state.get("violations"),
        "warnings": state.get("warnings"),
        "actions_taken": state.get("actions_taken"),
        "notifications_sent": state.get("notifications_sent"),
        "provisioning": state.get("provisioning"),
    }
    generated_files["audit_json"] = save_audit_json(
        f"audit_{account_id}_{timestamp}.json",
        audit_data
    )
    
    return generated_files

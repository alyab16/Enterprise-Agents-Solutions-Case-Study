"""
Mock notification service for Slack and Email.
In production, this would integrate with Slack API and SendGrid/SES.
"""

from datetime import datetime
from typing import Optional
from app.logging.logger import log_event

# Store sent notifications for demo/testing
_SENT_NOTIFICATIONS = []


def send_slack_message(
    channel: str,
    message: str,
    *,
    account_id: Optional[str] = None,
    correlation_id: Optional[str] = None,
    urgency: str = "normal",
    blocks: Optional[list] = None,
) -> dict:
    """
    Send a Slack message to a channel or user.
    
    In production, this would use the Slack Web API.
    """
    notification = {
        "type": "slack",
        "channel": channel,
        "message": message,
        "urgency": urgency,
        "blocks": blocks,
        "account_id": account_id,
        "correlation_id": correlation_id,
        "sent_at": datetime.utcnow().isoformat(),
        "status": "sent",
    }
    
    _SENT_NOTIFICATIONS.append(notification)
    
    log_event(
        "notification.slack.sent",
        channel=channel,
        account_id=account_id,
        urgency=urgency,
    )
    
    # Mock response
    return {
        "ok": True,
        "channel": channel,
        "ts": f"mock-{datetime.utcnow().timestamp()}",
        "message": notification,
    }


def send_email(
    to: str,
    subject: str,
    body: str,
    *,
    account_id: Optional[str] = None,
    correlation_id: Optional[str] = None,
    cc: Optional[list] = None,
    template: Optional[str] = None,
) -> dict:
    """
    Send an email notification.
    
    In production, this would use SendGrid, AWS SES, etc.
    """
    notification = {
        "type": "email",
        "to": to,
        "cc": cc,
        "subject": subject,
        "body": body,
        "template": template,
        "account_id": account_id,
        "correlation_id": correlation_id,
        "sent_at": datetime.utcnow().isoformat(),
        "status": "sent",
    }
    
    _SENT_NOTIFICATIONS.append(notification)
    
    log_event(
        "notification.email.sent",
        to=to,
        subject=subject,
        account_id=account_id,
    )
    
    # Mock response
    return {
        "ok": True,
        "message_id": f"mock-email-{datetime.utcnow().timestamp()}",
        "notification": notification,
    }


def get_sent_notifications(account_id: Optional[str] = None) -> list:
    """Retrieve sent notifications, optionally filtered by account."""
    if account_id:
        return [n for n in _SENT_NOTIFICATIONS if n.get("account_id") == account_id]
    return _SENT_NOTIFICATIONS.copy()


def clear_notifications():
    """Clear notification history (for testing)."""
    _SENT_NOTIFICATIONS.clear()


# ----------------------------
# Pre-built notification templates
# ----------------------------

def notify_cs_team_blocked(
    account_name: str,
    account_id: str,
    violations: dict,
    correlation_id: str,
) -> dict:
    """Send urgent notification when onboarding is blocked."""
    
    violation_list = []
    for domain, msgs in violations.items():
        if isinstance(msgs, list):
            for msg in msgs:
                violation_list.append(f"• *{domain}*: {msg}")
        else:
            violation_list.append(f"• *{domain}*: {msgs}")
    
    message = f"""🚨 *Onboarding BLOCKED* for {account_name}

The automated onboarding process has encountered critical issues that require immediate attention.

*Violations:*
{chr(10).join(violation_list)}

*Next Steps:*
1. Review the violations above
2. Resolve data issues in source systems
3. Re-trigger onboarding when resolved

<https://crm.demo/accounts/{account_id}|View in Salesforce> | <https://agent.demo/runs/{correlation_id}|View Agent Run>
"""
    
    return send_slack_message(
        channel="#cs-onboarding-alerts",
        message=message,
        account_id=account_id,
        correlation_id=correlation_id,
        urgency="high",
    )


def notify_cs_team_escalation(
    account_name: str,
    account_id: str,
    warnings: dict,
    correlation_id: str,
) -> dict:
    """Send notification when onboarding needs human review."""
    
    warning_list = []
    for domain, msgs in warnings.items():
        if isinstance(msgs, list):
            for msg in msgs:
                warning_list.append(f"• *{domain}*: {msg}")
        else:
            warning_list.append(f"• *{domain}*: {msgs}")
    
    message = f"""⚠️ *Onboarding Needs Review* for {account_name}

The automated onboarding process has identified issues that may require your attention.

*Warnings:*
{chr(10).join(warning_list)}

*Recommended Actions:*
• Review warnings and determine if manual intervention needed
• Approve to proceed or resolve issues first

<https://crm.demo/accounts/{account_id}|View in Salesforce> | <https://agent.demo/runs/{correlation_id}|View Agent Run>
"""
    
    return send_slack_message(
        channel="#cs-onboarding",
        message=message,
        account_id=account_id,
        correlation_id=correlation_id,
        urgency="medium",
    )


def notify_cs_team_success(
    account_name: str,
    account_id: str,
    tenant_id: str,
    correlation_id: str,
) -> dict:
    """Send notification when onboarding completes successfully."""
    
    message = f"""✅ *Onboarding Complete* for {account_name}

The customer has been successfully provisioned and is ready to use the platform.

*Details:*
• Tenant ID: `{tenant_id}`
• Status: Active

*Next Steps:*
• Schedule kickoff call with customer
• Send welcome email with login credentials
• Assign to onboarding specialist

<https://app.demo/admin/{tenant_id}|View Tenant> | <https://agent.demo/runs/{correlation_id}|View Agent Run>
"""
    
    return send_slack_message(
        channel="#cs-onboarding",
        message=message,
        account_id=account_id,
        correlation_id=correlation_id,
        urgency="low",
    )


def send_customer_welcome_email(
    customer_email: str,
    customer_name: str,
    account_name: str,
    tenant_id: str,
    account_id: str,
    correlation_id: str,
) -> dict:
    """Send welcome email to the customer."""
    
    subject = f"Welcome to StackAdapt, {account_name}!"
    
    body = f"""Hi {customer_name},

Welcome to StackAdapt! Your account has been provisioned and you're ready to get started.

Here are your account details:
- Tenant ID: {tenant_id}
- Login URL: https://app.stackadapt.demo/login

Getting Started:
1. Log in using your email address
2. Complete the platform tour
3. Set up your first campaign

Your Customer Success Manager will reach out shortly to schedule a kickoff call.

If you have any questions, don't hesitate to reach out.

Best regards,
The StackAdapt Team
"""
    
    return send_email(
        to=customer_email,
        subject=subject,
        body=body,
        account_id=account_id,
        correlation_id=correlation_id,
        template="customer_welcome",
    )


def notify_onboarding_escalation(
    account_name: str,
    account_id: str,
    reason: str,
    progress_snapshot: dict,
    correlation_id: str = "",
) -> dict:
    """Send Slack notification for escalated/stalled onboarding."""

    pct = progress_snapshot.get("completion", 0)
    days = progress_snapshot.get("days_since_provisioning", 0)
    overdue = progress_snapshot.get("overdue_count", 0)
    blocked = progress_snapshot.get("blocked_count", 0)

    message = f"""🔔 *Onboarding Escalation* for {account_name}

*Reason:* {reason}

*Progress Snapshot:*
• Completion: {pct}%
• Days since provisioning: {days}
• Overdue tasks: {overdue}
• Blocked tasks: {blocked}

*Next Steps:*
1. Review blocked/overdue tasks
2. Contact customer if unresponsive
3. Assign additional CS resources if needed

<https://crm.demo/accounts/{account_id}|View in Salesforce>
"""

    return send_slack_message(
        channel="#cs-onboarding-escalations",
        message=message,
        account_id=account_id,
        correlation_id=correlation_id,
        urgency="high",
    )


def notify_finance_overdue_invoice(
    account_name: str,
    account_id: str,
    invoice_id: str,
    amount: float,
    days_overdue: int,
    correlation_id: str,
) -> dict:
    """Escalate overdue invoice to finance team."""
    
    message = f"""💰 *Overdue Invoice Alert* for {account_name}

An onboarding is blocked due to an overdue invoice.

*Invoice Details:*
• Invoice ID: `{invoice_id}`
• Amount: ${amount:,.2f}
• Days Overdue: {days_overdue}

*Impact:*
Customer onboarding cannot proceed until payment is resolved.

<https://netsuite.demo/invoices/{invoice_id}|View Invoice> | <https://agent.demo/runs/{correlation_id}|View Agent Run>
"""
    
    return send_slack_message(
        channel="#finance-alerts",
        message=message,
        account_id=account_id,
        correlation_id=correlation_id,
        urgency="high",
    )

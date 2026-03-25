"""
FastMCP server for notification dispatch (Slack + Email).

Exposes notification functions as MCP tools. The agent decides
which notifications to send based on its decision.

Tools:
- notify_blocked: Alert CS team about blocked onboarding
- notify_escalation: Alert CS team about escalation
- notify_success: Confirm successful provisioning
- notify_finance_overdue: Escalate overdue invoice to finance
- send_customer_welcome: Send welcome email to customer
- send_email: Send a generic email
"""

from fastmcp import FastMCP

mcp = FastMCP(
    name="notifications",
    instructions=(
        "Notification system for Slack and email. Send appropriate notifications "
        "based on the onboarding decision: blocked → urgent alerts, escalation → "
        "review requests, proceed → success confirmations and welcome emails."
    ),
)


@mcp.tool()
def notify_blocked(
    account_name: str,
    account_id: str,
    violations: dict,
    correlation_id: str,
) -> dict:
    """
    Send urgent Slack notification when onboarding is BLOCKED.
    Alerts the CS team with violation details and next steps.
    """
    from app.notifications import notifier

    return notifier.notify_cs_team_blocked(
        account_name=account_name,
        account_id=account_id,
        violations=violations,
        correlation_id=correlation_id,
    )


@mcp.tool()
def notify_escalation(
    account_name: str,
    account_id: str,
    warnings: dict,
    correlation_id: str,
) -> dict:
    """
    Send Slack notification when onboarding needs human ESCALATION review.
    Alerts the CS team with warning details.
    """
    from app.notifications import notifier

    return notifier.notify_cs_team_escalation(
        account_name=account_name,
        account_id=account_id,
        warnings=warnings,
        correlation_id=correlation_id,
    )


@mcp.tool()
def notify_success(
    account_name: str,
    account_id: str,
    tenant_id: str,
    correlation_id: str,
) -> dict:
    """
    Send Slack notification when onboarding completes successfully.
    Confirms provisioning to the CS team.
    """
    from app.notifications import notifier

    return notifier.notify_cs_team_success(
        account_name=account_name,
        account_id=account_id,
        tenant_id=tenant_id,
        correlation_id=correlation_id,
    )


@mcp.tool()
def notify_finance_overdue(
    account_name: str,
    account_id: str,
    invoice_id: str,
    amount: float,
    days_overdue: int,
    correlation_id: str,
) -> dict:
    """
    Escalate overdue invoice to finance team via Slack.
    Use when an invoice is OVERDUE and blocking or delaying onboarding.
    """
    from app.notifications import notifier

    return notifier.notify_finance_overdue_invoice(
        account_name=account_name,
        account_id=account_id,
        invoice_id=invoice_id,
        amount=amount,
        days_overdue=days_overdue,
        correlation_id=correlation_id,
    )


@mcp.tool()
def send_customer_welcome(
    customer_email: str,
    customer_name: str,
    account_name: str,
    tenant_id: str,
    account_id: str,
    correlation_id: str,
) -> dict:
    """
    Send welcome email to the customer with login instructions.
    Use after successful provisioning.
    """
    from app.notifications import notifier

    return notifier.send_customer_welcome_email(
        customer_email=customer_email,
        customer_name=customer_name,
        account_name=account_name,
        tenant_id=tenant_id,
        account_id=account_id,
        correlation_id=correlation_id,
    )


@mcp.tool()
def send_email(
    to: str,
    subject: str,
    body: str,
    account_id: str = "",
    correlation_id: str = "",
) -> dict:
    """Send a generic email notification."""
    from app.notifications import notifier

    return notifier.send_email(
        to=to,
        subject=subject,
        body=body,
        account_id=account_id,
        correlation_id=correlation_id,
    )


if __name__ == "__main__":
    mcp.run()

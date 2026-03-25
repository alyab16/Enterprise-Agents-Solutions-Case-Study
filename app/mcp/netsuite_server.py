"""
FastMCP server for NetSuite ERP integration.

Exposes invoice and billing data as MCP tools. Wraps the existing
NetSuite integration module.

Tools:
- get_invoice: Fetch invoice by account ID
- get_invoice_status: Get just the invoice status
- get_outstanding_amount: Get outstanding balance
"""

from fastmcp import FastMCP

mcp = FastMCP(
    name="netsuite",
    instructions=(
        "NetSuite ERP integration for invoice and billing data. Use these tools "
        "to check payment status. Overdue invoices trigger escalation, voided or "
        "cancelled invoices block onboarding."
    ),
)


@mcp.tool()
def get_invoice(account_id: str) -> dict:
    """
    Fetch invoice data for an account from NetSuite.

    Returns invoice details including status (PAID, OPEN, OVERDUE, DRAFT,
    VOIDED, CANCELLED), total, amount_remaining, due_date, and days_overdue.
    Check for error statuses like AUTH_ERROR, SERVER_ERROR.
    """
    from app.integrations import netsuite

    return netsuite.get_invoice(account_id)


@mcp.tool()
def get_invoice_status(account_id: str) -> str:
    """Get just the invoice status string for an account."""
    from app.integrations import netsuite

    return netsuite.get_invoice_status(account_id)


@mcp.tool()
def get_outstanding_amount(account_id: str) -> float:
    """Get outstanding payment amount for an account."""
    from app.integrations import netsuite

    return netsuite.get_outstanding_amount(account_id)


if __name__ == "__main__":
    mcp.run()

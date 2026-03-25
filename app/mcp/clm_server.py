"""
FastMCP server for Contract Lifecycle Management (CLM) integration.

Exposes CLM contract data as MCP tools. Wraps the existing CLM
integration module for MCP-style access.

Tools:
- get_contract: Fetch CLM contract by account ID
- get_contract_status: Get just the contract status
- get_pending_signatories: Get signatories who haven't signed
"""

from fastmcp import FastMCP

mcp = FastMCP(
    name="clm",
    instructions=(
        "Contract Lifecycle Management integration. Use these tools to check "
        "contract execution status and signatory completion. A contract must be "
        "SIGNED or EXECUTED for onboarding to proceed."
    ),
)


@mcp.tool()
def get_contract(account_id: str) -> dict:
    """
    Fetch CLM contract data for an account.

    Returns contract details including status (EXECUTED, SIGNED, DRAFT,
    PENDING_SIGNATURE, etc.), signatories, effective/expiry dates, and
    key terms (SLA tier, payment terms). Check for error statuses like
    AUTH_ERROR, PERMISSION_ERROR, SERVER_ERROR.
    """
    from app.integrations import clm

    return clm.get_contract(account_id)


@mcp.tool()
def get_contract_status(account_id: str) -> str:
    """Get just the contract status string for an account."""
    from app.integrations import clm

    return clm.get_contract_status(account_id)


@mcp.tool()
def get_pending_signatories(account_id: str) -> list:
    """Get list of signatories who haven't signed the contract yet."""
    from app.integrations import clm

    return clm.get_pending_signatories(account_id)


if __name__ == "__main__":
    mcp.run()

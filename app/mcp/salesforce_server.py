"""
FastMCP server for Salesforce CRM integration.

Exposes Salesforce data retrieval as MCP tools. In production, this server
would run as a standalone HTTP service. For now, these tool definitions
mirror the in-process tools registered on the Pydantic AI agent.

Tools:
- get_account: Fetch account by ID
- get_user: Fetch user/owner by ID
- get_opportunity_by_account: Fetch opportunity linked to account
- get_contract_by_account: Fetch contract linked to account
"""

from fastmcp import FastMCP

mcp = FastMCP(
    name="salesforce",
    instructions=(
        "Salesforce CRM integration. Use these tools to fetch account, user, "
        "opportunity, and contract data. Check for API_ERROR status in responses "
        "— these indicate integration failures that block onboarding."
    ),
)


@mcp.tool()
def get_account(account_id: str) -> dict:
    """
    Fetch account data from Salesforce by account ID.

    Returns the full account record including Name, Industry, BillingCountry,
    OwnerId, and IsDeleted flag. If the account is not found, returns
    {"status": "NOT_FOUND"}. If Salesforce returns an error, returns
    {"status": "API_ERROR", ...} with error details.
    """
    from app.integrations import salesforce

    result = salesforce.get_account(account_id)
    if result is None:
        return {"status": "NOT_FOUND", "account_id": account_id}
    return result


@mcp.tool()
def get_user(user_id: str) -> dict:
    """
    Fetch user/owner data from Salesforce by user ID.

    Returns user profile including Email, IsActive, Department, Title.
    Needed to validate the account owner is active and properly configured.
    """
    from app.integrations import salesforce

    result = salesforce.get_user(user_id)
    if result is None:
        return {"status": "NOT_FOUND", "user_id": user_id}
    return result


@mcp.tool()
def get_opportunity_by_account(account_id: str) -> dict:
    """
    Fetch the opportunity linked to an account.

    Returns opportunity details including StageName (must be "Closed Won"
    for onboarding to proceed), Amount, and CloseDate.
    """
    from app.integrations import salesforce

    result = salesforce.get_opportunity_by_account(account_id)
    if result is None:
        return {"status": "NOT_FOUND", "account_id": account_id}
    return result


@mcp.tool()
def get_contract_by_account(account_id: str) -> dict:
    """
    Fetch the Salesforce contract linked to an account.

    Returns contract details including Status and ownership.
    Note: This is the Salesforce contract record, separate from the CLM contract.
    """
    from app.integrations import salesforce

    result = salesforce.get_contract_by_account(account_id)
    if result is None:
        return {"status": "NOT_FOUND", "account_id": account_id}
    return result


if __name__ == "__main__":
    mcp.run()

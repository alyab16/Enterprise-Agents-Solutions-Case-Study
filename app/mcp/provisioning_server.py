"""
FastMCP server for SaaS tenant provisioning.

Exposes provisioning and onboarding task management as MCP tools.
Only use provisioning tools when the decision is PROCEED.

Tools:
- provision_account: Create tenant and onboarding tasks
- get_onboarding_tasks: List all onboarding tasks
- get_provisioning_status: Check if already provisioned
"""

from fastmcp import FastMCP

mcp = FastMCP(
    name="provisioning",
    instructions=(
        "SaaS provisioning system. Use provision_account ONLY when the onboarding "
        "decision is PROCEED (no violations, no API errors). This creates a tenant, "
        "generates API credentials, and sets up onboarding task checklist."
    ),
)


@mcp.tool()
def provision_account(account_id: str, tier: str = "Starter", customer_name: str = "Customer") -> dict:
    """
    Provision a new tenant in the SaaS platform.

    Creates: tenant ID, API credentials, admin URL, and a full onboarding
    task checklist (14 tasks across automated, CS team, and customer categories).

    Args:
        account_id: The account to provision
        tier: Service tier (Enterprise, Growth, or Starter)
        customer_name: Customer's company name
    """
    from app.integrations import provisioning

    return provisioning.provision_account(account_id, tier, customer_name)


@mcp.tool()
def get_onboarding_tasks(account_id: str) -> list:
    """Get all onboarding tasks for a provisioned account."""
    from app.integrations import provisioning

    return provisioning.get_onboarding_tasks(account_id)


@mcp.tool()
def get_provisioning_status(account_id: str) -> dict:
    """Check if an account has already been provisioned."""
    from app.integrations import provisioning

    return provisioning.get_provisioning_status(account_id)


if __name__ == "__main__":
    mcp.run()

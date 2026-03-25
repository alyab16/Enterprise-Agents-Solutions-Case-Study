"""
FastMCP server for business rule validation.

Exposes invariant checks as MCP tools. These encode the business rules
that determine whether onboarding can proceed.

Tools:
- validate_all: Run all business rule validations on collected data
"""

from fastmcp import FastMCP

mcp = FastMCP(
    name="validation",
    instructions=(
        "Business rule validation engine. Use validate_all after fetching data "
        "from all systems. Returns violations (blocking issues) and warnings "
        "(non-blocking concerns). Violations → BLOCK, Warnings → ESCALATE."
    ),
)


@mcp.tool()
def validate_all(
    account: dict = None,
    user: dict = None,
    opportunity: dict = None,
    contract: dict = None,
    invoice: dict = None,
    clm: dict = None,
) -> dict:
    """
    Run all business rule validations on the collected data.

    Checks invariants for each domain:
    - Account: required fields, not deleted
    - User/Owner: active, has required fields
    - Opportunity: must be Closed Won
    - Contract (CLM): must be SIGNED or EXECUTED
    - Invoice: valid status, not voided/cancelled

    Returns:
        {
            "violations": {"domain": ["blocking issue 1", ...]},
            "warnings": {"domain": ["non-blocking concern 1", ...]}
        }
    """
    from app.agent.invariants import (
        check_account_invariants,
        check_user_invariants,
        check_opportunity_invariants,
        check_contract_invariants,
        check_invoice_invariants,
    )

    # Build a minimal state dict for the invariant checkers
    state = {
        "account": account,
        "user": user,
        "opportunity": opportunity,
        "contract": contract,
        "invoice": invoice,
        "clm": clm,
        "violations": {},
        "warnings": {},
    }

    check_account_invariants(state)
    check_user_invariants(state)
    check_opportunity_invariants(state)
    check_contract_invariants(state)
    check_invoice_invariants(state)

    return {
        "violations": state.get("violations", {}),
        "warnings": state.get("warnings", {}),
    }


if __name__ == "__main__":
    mcp.run()

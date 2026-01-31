from app.agent.state_utils import add_violation, add_warning


def check_account_invariants(state: dict) -> None:
    """
    Validate account data against business rules.
    
    Tier 1: Hard requirements (violations -> BLOCK)
    Tier 2: Business readiness (warnings -> ESCALATE)
    """
    account = state.get("account")

    # ----------------------------
    # Existence check
    # ----------------------------
    if not account:
        add_violation(state, "account", "Account data missing")
        return

    # ----------------------------
    # Tier 1 – Hard requirements
    # ----------------------------
    if not account.get("Id"):
        add_violation(state, "account", "Account.Id is required")

    if not account.get("Name"):
        add_violation(state, "account", "Account.Name is required")

    if account.get("IsDeleted") is True:
        add_violation(state, "account", "Account is marked as deleted")

    # ----------------------------
    # Tier 2 – Business readiness
    # ----------------------------
    if not account.get("BillingCountry"):
        add_warning(state, "account", "BillingCountry missing; tax/provisioning may fail")

    if not account.get("Industry"):
        add_warning(state, "account", "Industry not set; segmentation limited")

    if not account.get("OwnerId"):
        add_warning(state, "account", "Account has no assigned owner")

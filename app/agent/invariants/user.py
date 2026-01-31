from app.agent.state_utils import add_violation, add_warning


def check_user_invariants(state: dict) -> None:
    """
    Validate user (account owner) data against business rules.
    
    Tier 1: Identity & access (violations -> BLOCK)
    Tier 2: Operational readiness (warnings -> ESCALATE)
    """
    user = state.get("user")

    # ----------------------------
    # Existence check
    # ----------------------------
    if not user:
        add_violation(state, "user", "User data missing")
        return

    # ----------------------------
    # Tier 1 – Identity & access
    # ----------------------------
    if not user.get("Id"):
        add_violation(state, "user", "User.Id is required")

    if not user.get("Username"):
        add_violation(state, "user", "User.Username is required")

    if not user.get("Email"):
        add_violation(state, "user", "User.Email is required")

    if user.get("IsActive") is False:
        add_violation(state, "user", "User is inactive")

    if not user.get("ProfileId"):
        add_violation(state, "user", "User.ProfileId is required")

    # Portal users must have an Account
    if user.get("IsPortalEnabled") is True:
        if not user.get("AccountId"):
            add_violation(state, "user", "Portal user must be associated with an Account")

    # ----------------------------
    # Tier 2 – Operational readiness
    # ----------------------------
    if not user.get("FirstName") or not user.get("LastName"):
        add_warning(state, "user", "User full name incomplete")

    if not user.get("Title"):
        add_warning(state, "user", "User.Title missing")

    if not user.get("Department"):
        add_warning(state, "user", "User.Department missing")

    if not user.get("TimeZoneSidKey"):
        add_warning(state, "user", "User.TimeZoneSidKey missing")

    if not user.get("ManagerId"):
        add_warning(state, "user", "User has no ManagerId (escalation risk)")

from app.agent.state_utils import add_violation, add_warning

WON_STAGES = {"Closed Won"}
OPEN_STAGES = {"Prospecting", "Qualification", "Needs Analysis", 
               "Value Proposition", "Negotiation", "Proposal"}


def check_opportunity_invariants(state: dict) -> None:
    """
    Validate opportunity data against business rules.
    
    Tier 1: Deal validity (violations -> BLOCK)
    Tier 2: Commercial readiness (warnings -> ESCALATE)
    """
    opportunity = state.get("opportunity")

    # ----------------------------
    # Existence check
    # ----------------------------
    if not opportunity:
        add_violation(state, "opportunity", "Opportunity data missing")
        return

    stage = opportunity.get("StageName")

    # ----------------------------
    # Tier 1 – Deal validity
    # ----------------------------
    if not opportunity.get("Id"):
        add_violation(state, "opportunity", "Opportunity.Id is required")

    if not opportunity.get("AccountId"):
        add_violation(state, "opportunity", "Opportunity.AccountId is required")

    if not stage:
        add_violation(state, "opportunity", "Opportunity.StageName is required")

    if stage and stage not in WON_STAGES and stage not in OPEN_STAGES:
        add_violation(state, "opportunity", f"Invalid StageName: {stage}")

    # Must be Closed Won for onboarding to proceed
    if stage and stage not in WON_STAGES:
        add_violation(state, "opportunity", f"Opportunity not won (stage: {stage})")

    # ----------------------------
    # Tier 2 – Commercial readiness
    # ----------------------------
    if stage in WON_STAGES:
        if not opportunity.get("Amount"):
            add_warning(state, "opportunity", "Closed Won opportunity has no Amount")

        if not opportunity.get("CloseDate"):
            add_warning(state, "opportunity", "Closed Won opportunity missing CloseDate")

        if not opportunity.get("OwnerId"):
            add_warning(state, "opportunity", "Closed Won opportunity has no OwnerId")

        if not opportunity.get("ContractId"):
            add_warning(state, "opportunity", "Closed Won opportunity not linked to Contract")

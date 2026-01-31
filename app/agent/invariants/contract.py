from app.agent.state_utils import add_violation, add_warning

VALID_STATUSES = {"Draft", "In Approval Process", "Activated"}


def check_contract_invariants(state: dict) -> None:
    """
    Validate contract data against business rules.
    
    Tier 1: Lifecycle validity (violations -> BLOCK)
    Tier 2: Business readiness (warnings -> ESCALATE)
    """
    contract = state.get("contract")

    # ----------------------------
    # Existence check
    # ----------------------------
    if not contract:
        add_violation(state, "contract", "Contract data missing")
        return

    status = contract.get("Status")

    # ----------------------------
    # Tier 1 – Lifecycle validity
    # ----------------------------
    if not contract.get("AccountId"):
        add_violation(state, "contract", "Contract.AccountId is required")

    if not contract.get("StartDate"):
        add_violation(state, "contract", "Contract.StartDate is required")

    if status not in VALID_STATUSES:
        add_violation(state, "contract", f"Invalid contract status: {status}")

    if status == "Activated" and not contract.get("ActivatedDate"):
        add_violation(state, "contract", "Activated contracts must have ActivatedDate")

    # ----------------------------
    # Tier 2 – Business readiness
    # ----------------------------
    if not contract.get("OwnerId"):
        add_warning(state, "contract", "Contract has no assigned owner")

    if not contract.get("EndDate") and not contract.get("ContractTerm"):
        add_warning(state, "contract", "Contract has no EndDate or ContractTerm")

    if status == "Activated" and not contract.get("CustomerSignedDate"):
        add_warning(state, "contract", "Activated contract missing CustomerSignedDate")
    
    if status == "Draft":
        add_warning(state, "contract", "Contract still in Draft status")
    
    if status == "In Approval Process":
        add_warning(state, "contract", "Contract pending approval")

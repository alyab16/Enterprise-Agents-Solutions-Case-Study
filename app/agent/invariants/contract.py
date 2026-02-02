from app.agent.state_utils import add_violation, add_warning

# Valid CLM contract statuses
VALID_CLM_STATUSES = {"DRAFT", "SENT", "SIGNED", "EXECUTED", "EXPIRED", "VOIDED"}

# Statuses that allow onboarding to proceed
PROCEED_STATUSES = {"EXECUTED", "SIGNED"}


def check_contract_invariants(state: dict) -> None:
    """
    Validate CLM contract data against business rules.
    
    NOTE: This checks CLM data (stored in state["clm"]), which is the source 
    of truth for contract signatures. The Salesforce Contract object 
    (state["contract"]) is separate and used for different purposes.
    
    CLM uses lowercase field names: status, contract_id, effective_date, etc.
    
    Tier 1: Lifecycle validity (violations -> BLOCK)
    Tier 2: Business readiness (warnings -> ESCALATE)
    """
    # CLM data is stored in state["clm"]
    clm_contract = state.get("clm")

    # ----------------------------
    # Existence check
    # ----------------------------
    if not clm_contract:
        add_violation(state, "contract", "CLM contract data missing - cannot verify signatures")
        return
    
    # Check for API error response (when CLM fetch failed)
    if clm_contract.get("status") in {"AUTH_ERROR", "PERMISSION_ERROR", "SERVER_ERROR", "API_ERROR", "NOT_FOUND", "VALIDATION_ERROR", "RATE_LIMIT_ERROR"}:
        # This is an error response, not contract data - skip validation
        # The error is already recorded in api_errors by nodes.py
        return

    status = (clm_contract.get("status") or "").upper()
    
    # ----------------------------
    # Tier 1 – Lifecycle validity
    # ----------------------------
    if not clm_contract.get("contract_id"):
        add_violation(state, "contract", "CLM contract ID is missing")

    if status and status not in VALID_CLM_STATUSES:
        add_violation(state, "contract", f"Invalid CLM contract status: {status}")
    
    # Contract must be EXECUTED or SIGNED to proceed with onboarding
    if status and status not in PROCEED_STATUSES:
        if status == "DRAFT":
            add_violation(state, "contract", "Contract is still in DRAFT - not yet sent for signatures")
        elif status == "SENT":
            add_violation(state, "contract", "Contract sent but awaiting signatures - cannot proceed")
        elif status == "EXPIRED":
            add_violation(state, "contract", "Contract has EXPIRED - needs renewal")
        elif status == "VOIDED":
            add_violation(state, "contract", "Contract has been VOIDED - cannot proceed")
        else:
            add_violation(state, "contract", f"Contract status '{status}' does not allow onboarding")

    # ----------------------------
    # Tier 2 – Business readiness
    # ----------------------------
    if not clm_contract.get("effective_date"):
        add_warning(state, "contract", "Contract has no effective date set")
    
    if not clm_contract.get("expiry_date"):
        add_warning(state, "contract", "Contract has no expiry date - renewal tracking limited")
    
    # Check for pending signatories (should be empty for EXECUTED status)
    pending = clm_contract.get("pending_signatories", [])
    if pending:
        names = [s.get("name", "Unknown") for s in pending]
        add_warning(state, "contract", f"Signatures still pending from: {', '.join(names)}")

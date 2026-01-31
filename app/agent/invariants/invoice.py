from app.agent.state_utils import add_violation, add_warning

VALID_INVOICE_STATUSES = {"PAID", "OPEN", "PENDING", "OVERDUE", "DRAFT", "VOIDED", "CANCELLED"}


def check_invoice_invariants(state: dict) -> None:
    """
    Validate invoice (NetSuite) data against business rules.
    
    NetSuite Status Mapping:
    - A (Open) → OPEN or OVERDUE (based on due date)
    - B (Paid In Full) → PAID
    - E (Pending Approval) → DRAFT
    - V (Voided) → VOIDED
    
    Tier 1: Payment validity (violations -> BLOCK for provisioning)
    Tier 2: Business readiness (warnings -> ESCALATE)
    """
    invoice = state.get("invoice")

    # ----------------------------
    # Existence check
    # ----------------------------
    if not invoice:
        add_warning(state, "invoice", "Invoice data not found in NetSuite")
        return
    
    # Check for API errors
    if invoice.get("status") == "NOT_FOUND":
        add_warning(state, "invoice", "No invoice found for this account")
        return
    
    if invoice.get("status") == "API_ERROR":
        add_warning(state, "invoice", f"NetSuite API error: {invoice.get('error', 'Unknown')}")
        return

    status = invoice.get("status")
    invoice_id = invoice.get("invoice_id", "Unknown")

    # ----------------------------
    # Tier 1 – Payment validity
    # ----------------------------
    if not invoice.get("invoice_id"):
        add_violation(state, "invoice", "Invoice ID is missing")

    if status not in VALID_INVOICE_STATUSES:
        add_violation(state, "invoice", f"Invalid invoice status: {status}")

    if status == "VOIDED":
        add_violation(state, "invoice", f"Invoice {invoice_id} has been voided")
    
    if status == "CANCELLED":
        add_violation(state, "invoice", f"Invoice {invoice_id} has been cancelled")

    # ----------------------------
    # Tier 2 – Payment readiness
    # ----------------------------
    if status == "OPEN":
        amount_remaining = invoice.get("amount_remaining", 0)
        add_warning(state, "invoice", 
            f"Invoice {invoice_id} is open with ${amount_remaining:,.2f} remaining")
    
    if status == "OVERDUE":
        days_overdue = invoice.get("days_overdue", 0)
        amount_remaining = invoice.get("amount_remaining", 0)
        add_warning(state, "invoice", 
            f"Invoice {invoice_id} is {days_overdue} days overdue (${amount_remaining:,.2f} outstanding) - escalate to Finance")
    
    if status == "DRAFT":
        add_warning(state, "invoice", 
            f"Invoice {invoice_id} is still in draft/pending approval - not yet sent to customer")

    # ----------------------------
    # Tier 2 – Data completeness
    # ----------------------------
    if not invoice.get("total") and invoice.get("total") != 0:
        add_warning(state, "invoice", "Invoice total amount is missing")
    
    if not invoice.get("due_date"):
        add_warning(state, "invoice", "Invoice due date is missing")
    
    if not invoice.get("customer_email"):
        add_warning(state, "invoice", "Customer email missing on invoice - cannot send reminders")
    
    # Check for large outstanding amounts
    amount_remaining = invoice.get("amount_remaining", 0)
    total = invoice.get("total", 0)
    if total > 0 and amount_remaining > 0:
        paid_percentage = ((total - amount_remaining) / total) * 100
        if paid_percentage < 50 and status not in ["PAID", "DRAFT"]:
            add_warning(state, "invoice", 
                f"Less than 50% of invoice paid ({paid_percentage:.0f}%)")

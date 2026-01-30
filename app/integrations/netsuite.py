MOCK_NETSUITE = {
    "ACME-001": {"invoice_id": "INV-1", "status": "PAID"},
    "BETA-002": {"invoice_id": "INV-2", "status": "UNPAID"},
}


def get_invoice(account_id: str) -> dict:
    return MOCK_NETSUITE.get(
        account_id,
        {"invoice_id": None, "status": "MISSING"},
    )

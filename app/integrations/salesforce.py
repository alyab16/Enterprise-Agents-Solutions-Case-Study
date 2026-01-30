MOCK_SALESFORCE = {
    "ACME-001": {"stage": "Closed Won", "cs_owner": "cs@stackadapt.demo"},
    "BETA-002": {"stage": "Negotiation", "cs_owner": "cs@stackadapt.demo"},
}


def get_account(account_id: str) -> dict:
    if account_id not in MOCK_SALESFORCE:
        raise ValueError("Salesforce account not found")
    return MOCK_SALESFORCE[account_id]

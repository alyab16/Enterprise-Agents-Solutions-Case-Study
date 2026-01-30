MOCK_CLM = {
    "ACME-001": {"contract_id": "CTR-1", "status": "EXECUTED"},
    "BETA-002": {"contract_id": "CTR-2", "status": "DRAFT"},
}


def get_contract(account_id: str) -> dict:
    return MOCK_CLM.get(
        account_id,
        {"contract_id": None, "status": "MISSING"},
    )

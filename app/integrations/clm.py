"""
Mock CLM (Contract Lifecycle Management) integration.
In production, this would integrate with tools like DocuSign CLM, Ironclad, etc.
"""

MOCK_CLM = {
    "ACME-001": {
        "contract_id": "CLM-CTR-001",
        "status": "EXECUTED",
        "signed_date": "2023-12-20",
        "expiry_date": "2024-12-31",
        "signatories": [
            {"name": "John Smith", "role": "CEO", "signed": True},
            {"name": "Sarah Johnson", "role": "CS Manager", "signed": True},
        ],
        "key_terms": {
            "payment_terms": "Net 30",
            "auto_renewal": True,
            "sla_tier": "Enterprise",
        }
    },
    "BETA-002": {
        "contract_id": "CLM-CTR-002",
        "status": "PENDING_SIGNATURE",
        "sent_date": "2024-01-10",
        "signatories": [
            {"name": "Jane Doe", "role": "CFO", "signed": False},
            {"name": "Sarah Johnson", "role": "CS Manager", "signed": True},
        ],
        "key_terms": {
            "payment_terms": "Net 45",
            "auto_renewal": False,
            "sla_tier": "Growth",
        }
    },
    "GAMMA-003": {
        "contract_id": "CLM-CTR-003",
        "status": "DRAFT",
        "created_date": "2024-01-18",
        "key_terms": {
            "payment_terms": "Net 30",
            "sla_tier": "Starter",
        }
    },
}


def get_contract(account_id: str) -> dict:
    """Fetch contract status from CLM system."""
    return MOCK_CLM.get(
        account_id,
        {"contract_id": None, "status": "NOT_FOUND"},
    )


def get_contract_status(account_id: str) -> str:
    """Get just the contract status."""
    contract = get_contract(account_id)
    return contract.get("status", "UNKNOWN")


def get_pending_signatories(account_id: str) -> list:
    """Get list of signatories who haven't signed yet."""
    contract = get_contract(account_id)
    signatories = contract.get("signatories", [])
    return [s for s in signatories if not s.get("signed")]

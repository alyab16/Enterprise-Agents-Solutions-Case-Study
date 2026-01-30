import uuid

_PROVISIONED = {}


def provision(account_id: str) -> dict:
    if account_id in _PROVISIONED:
        return _PROVISIONED[account_id]

    tenant_id = f"TEN-{uuid.uuid4().hex[:8].upper()}"
    _PROVISIONED[account_id] = {
        "status": "ACTIVE",
        "tenant_id": tenant_id,
    }
    return _PROVISIONED[account_id]

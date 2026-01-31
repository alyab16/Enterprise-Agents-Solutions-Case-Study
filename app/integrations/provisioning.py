"""
Mock SaaS provisioning system integration.
In production, this would integrate with your product's provisioning API.
"""

import uuid
from datetime import datetime

# Track provisioned accounts
_PROVISIONED_ACCOUNTS = {}

MOCK_PROVISIONING_CONFIG = {
    "Enterprise": {
        "max_users": 100,
        "features": ["analytics", "api_access", "sso", "custom_reports", "dedicated_support"],
        "storage_gb": 500,
        "api_rate_limit": 10000,
    },
    "Growth": {
        "max_users": 25,
        "features": ["analytics", "api_access", "standard_reports"],
        "storage_gb": 100,
        "api_rate_limit": 5000,
    },
    "Starter": {
        "max_users": 5,
        "features": ["analytics", "basic_reports"],
        "storage_gb": 25,
        "api_rate_limit": 1000,
    },
}


def provision_account(account_id: str, tier: str = "Starter") -> dict:
    """
    Provision a new tenant in the SaaS platform.
    Returns provisioning details.
    """
    if account_id in _PROVISIONED_ACCOUNTS:
        return _PROVISIONED_ACCOUNTS[account_id]
    
    config = MOCK_PROVISIONING_CONFIG.get(tier, MOCK_PROVISIONING_CONFIG["Starter"])
    
    tenant_id = f"TEN-{uuid.uuid4().hex[:8].upper()}"
    
    provisioning_result = {
        "tenant_id": tenant_id,
        "account_id": account_id,
        "status": "ACTIVE",
        "tier": tier,
        "provisioned_at": datetime.utcnow().isoformat(),
        "config": config,
        "admin_url": f"https://app.stackadapt.demo/admin/{tenant_id}",
        "api_key": f"sk_live_{uuid.uuid4().hex}",
    }
    
    _PROVISIONED_ACCOUNTS[account_id] = provisioning_result
    return provisioning_result


def get_provisioning_status(account_id: str) -> dict:
    """Check if account is already provisioned."""
    if account_id in _PROVISIONED_ACCOUNTS:
        return _PROVISIONED_ACCOUNTS[account_id]
    return {"status": "NOT_PROVISIONED", "account_id": account_id}


def is_provisioned(account_id: str) -> bool:
    """Check if account has been provisioned."""
    return account_id in _PROVISIONED_ACCOUNTS


def deprovision_account(account_id: str) -> dict:
    """Deprovision an account (for testing/cleanup)."""
    if account_id in _PROVISIONED_ACCOUNTS:
        del _PROVISIONED_ACCOUNTS[account_id]
        return {"status": "DEPROVISIONED", "account_id": account_id}
    return {"status": "NOT_FOUND", "account_id": account_id}


def reset_all():
    """Reset all provisioned accounts (for testing)."""
    _PROVISIONED_ACCOUNTS.clear()

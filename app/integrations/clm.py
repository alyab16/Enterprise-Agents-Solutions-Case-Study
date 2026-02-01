"""
Mock CLM (Contract Lifecycle Management) REST API integration.

This simulates integration with CLM platforms like:
- DocuSign CLM
- Ironclad
- Agiloft
- Icertis

API endpoints simulated:
- GET /api/v1/contracts/{id} - Get contract details
- GET /api/v1/contracts?account_id={id} - Search by account
- POST /api/v1/contracts - Create contract
- POST /api/v1/contracts/{id}/send - Send for signature
- GET /api/v1/contracts/{id}/signatories - Get signatory status
"""

import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from app.logging.logger import log_event
from app.integrations.api_errors import (
    APICredentials,
    APIError,
    ErrorCategory,
    ERROR_SIMULATOR,
)


# ============================================================================
# CLM-SPECIFIC ERRORS
# ============================================================================

class CLMError(APIError):
    """Base CLM API error."""
    pass


class CLMAuthenticationError(CLMError):
    """Invalid API key or token."""
    def __init__(self, message: str = "Invalid API credentials", details: Dict = None):
        super().__init__(
            status_code=401,
            error_code="UNAUTHORIZED",
            message=message,
            category=ErrorCategory.AUTHENTICATION,
            details=details or {
                "error": "Invalid or expired API key",
                "documentation": "https://docs.clm.example/authentication"
            }
        )


class CLMAuthorizationError(CLMError):
    """User lacks permission to access resource."""
    def __init__(self, resource: str, action: str, details: Dict = None):
        super().__init__(
            status_code=403,
            error_code="FORBIDDEN",
            message=f"Access denied: cannot {action} {resource}",
            category=ErrorCategory.AUTHORIZATION,
            details=details or {
                "resource": resource,
                "action": action,
                "required_role": "Contract Administrator",
            }
        )


class CLMValidationError(CLMError):
    """Validation error on request data."""
    def __init__(self, field: str, value: Any, reason: str, details: Dict = None):
        super().__init__(
            status_code=400,
            error_code="VALIDATION_ERROR",
            message=f"Validation failed for '{field}': {reason}",
            category=ErrorCategory.VALIDATION,
            details=details or {
                "field": field,
                "value": str(value),
                "reason": reason,
            }
        )


class CLMNotFoundError(CLMError):
    """Contract or resource not found."""
    def __init__(self, resource_type: str, resource_id: str):
        super().__init__(
            status_code=404,
            error_code="NOT_FOUND",
            message=f"{resource_type} with ID '{resource_id}' not found",
            category=ErrorCategory.NOT_FOUND,
            details={
                "resource_type": resource_type,
                "resource_id": resource_id,
            }
        )


class CLMRateLimitError(CLMError):
    """API rate limit exceeded."""
    def __init__(self, limit: int, reset_seconds: int):
        super().__init__(
            status_code=429,
            error_code="RATE_LIMIT_EXCEEDED",
            message=f"Rate limit exceeded. Limit: {limit} requests per minute.",
            category=ErrorCategory.RATE_LIMIT,
            details={
                "limit": limit,
                "reset_in_seconds": reset_seconds,
                "retry_after": reset_seconds,
            }
        )


class CLMServerError(CLMError):
    """CLM server error."""
    def __init__(self, message: str = "Internal server error"):
        super().__init__(
            status_code=500,
            error_code="INTERNAL_ERROR",
            message=message,
            category=ErrorCategory.SERVER_ERROR,
            details={
                "support": "support@clm.example",
                "status_page": "https://status.clm.example"
            }
        )


class CLMContractLockedError(CLMError):
    """Contract is locked and cannot be modified."""
    def __init__(self, contract_id: str, locked_by: str):
        super().__init__(
            status_code=409,
            error_code="CONTRACT_LOCKED",
            message=f"Contract {contract_id} is locked for editing",
            category=ErrorCategory.VALIDATION,
            details={
                "contract_id": contract_id,
                "locked_by": locked_by,
                "lock_type": "exclusive_edit",
            }
        )


# ============================================================================
# API CONFIGURATION
# ============================================================================

CLM_CREDENTIALS = APICredentials(
    client_id="clm_api_key_mock",
    client_secret="clm_api_secret_mock",
    access_token="clm_bearer_token_mock",
    token_expiry=datetime.utcnow() + timedelta(hours=24),
    is_valid=True,
    permissions=["contracts.read", "contracts.write", "signatories.read"]
)


@dataclass
class CLMConfig:
    """CLM API configuration."""
    base_url: str = "https://api.clm.example/v1"
    credentials: APICredentials = None
    
    def __post_init__(self):
        if self.credentials is None:
            self.credentials = CLM_CREDENTIALS


_config = CLMConfig()


# ============================================================================
# MOCK DATA
# ============================================================================

MOCK_CLM_DB: Dict[str, Dict[str, Any]] = {
    "ACME-001": {
        "id": "CLM-CTR-001",
        "contract_id": "CLM-CTR-001",
        "external_id": "ACME-001",
        "name": "ACME Corp - Enterprise Service Agreement",
        "status": "EXECUTED",
        "status_details": {
            "code": "EXECUTED",
            "label": "Fully Executed",
            "description": "All parties have signed"
        },
        "created_date": "2023-12-01T10:00:00Z",
        "sent_date": "2023-12-15T09:00:00Z",
        "signed_date": "2023-12-20T14:30:00Z",
        "effective_date": "2024-01-01",
        "expiry_date": "2024-12-31",
        "signatories": [
            {
                "id": "SIG-001",
                "name": "John Smith",
                "email": "john.smith@acme.com",
                "role": "CEO",
                "company": "ACME Corp",
                "signed": True,
                "signed_date": "2023-12-18T10:00:00Z",
                "ip_address": "192.168.1.100",
            },
            {
                "id": "SIG-002",
                "name": "Sarah Johnson",
                "email": "sarah.johnson@stackadapt.com",
                "role": "CS Manager",
                "company": "StackAdapt",
                "signed": True,
                "signed_date": "2023-12-20T14:30:00Z",
                "ip_address": "10.0.0.50",
            },
        ],
        "key_terms": {
            "payment_terms": "Net 30",
            "auto_renewal": True,
            "renewal_notice_days": 30,
            "sla_tier": "Enterprise",
            "support_hours": "24/7",
            "data_retention_days": 365,
        },
        "documents": [
            {"id": "DOC-001", "name": "Master Service Agreement", "version": "1.0"},
            {"id": "DOC-002", "name": "Data Processing Agreement", "version": "1.0"},
        ],
        "audit_trail": [
            {"action": "created", "user": "system", "timestamp": "2023-12-01T10:00:00Z"},
            {"action": "sent_for_signature", "user": "sarah.johnson", "timestamp": "2023-12-15T09:00:00Z"},
            {"action": "signed", "user": "john.smith@acme.com", "timestamp": "2023-12-18T10:00:00Z"},
            {"action": "signed", "user": "sarah.johnson", "timestamp": "2023-12-20T14:30:00Z"},
            {"action": "executed", "user": "system", "timestamp": "2023-12-20T14:30:00Z"},
        ],
        "links": {
            "self": "/api/v1/contracts/CLM-CTR-001",
            "download": "/api/v1/contracts/CLM-CTR-001/download",
            "audit": "/api/v1/contracts/CLM-CTR-001/audit",
        }
    },
    "BETA-002": {
        "id": "CLM-CTR-002",
        "contract_id": "CLM-CTR-002",
        "external_id": "BETA-002",
        "name": "Beta Industries - Growth Service Agreement",
        "status": "PENDING_SIGNATURE",
        "status_details": {
            "code": "PENDING_SIGNATURE",
            "label": "Awaiting Signatures",
            "description": "Waiting for 1 signatory"
        },
        "created_date": "2024-01-05T10:00:00Z",
        "sent_date": "2024-01-10T09:00:00Z",
        "signatories": [
            {
                "id": "SIG-003",
                "name": "Jane Doe",
                "email": "jane.doe@beta.com",
                "role": "CFO",
                "company": "Beta Industries",
                "signed": False,
                "reminder_sent": True,
                "reminder_date": "2024-01-15T09:00:00Z",
            },
            {
                "id": "SIG-004",
                "name": "Sarah Johnson",
                "email": "sarah.johnson@stackadapt.com",
                "role": "CS Manager",
                "company": "StackAdapt",
                "signed": True,
                "signed_date": "2024-01-10T11:00:00Z",
            },
        ],
        "key_terms": {
            "payment_terms": "Net 45",
            "auto_renewal": False,
            "sla_tier": "Growth",
            "support_hours": "Business Hours",
        },
        "links": {
            "self": "/api/v1/contracts/CLM-CTR-002",
        }
    },
    "GAMMA-003": {
        "id": "CLM-CTR-003",
        "contract_id": "CLM-CTR-003",
        "external_id": "GAMMA-003",
        "name": "Gamma Startup - Starter Agreement",
        "status": "DRAFT",
        "status_details": {
            "code": "DRAFT",
            "label": "Draft",
            "description": "Contract is being prepared"
        },
        "created_date": "2024-01-18T10:00:00Z",
        "signatories": [],
        "key_terms": {
            "payment_terms": "Net 30",
            "sla_tier": "Starter",
            "support_hours": "Business Hours",
        },
        "links": {
            "self": "/api/v1/contracts/CLM-CTR-003",
        }
    },
    # Error simulation entries
    "AUTH-ERROR": {"_simulate_error": "authentication"},
    "PERM-ERROR": {"_simulate_error": "authorization"},
    "SERVER-ERROR": {"_simulate_error": "server"},
    "LOCKED-ERROR": {"_simulate_error": "locked"},
}


# ============================================================================
# CLM API CLIENT
# ============================================================================

class CLMClient:
    """
    Mock CLM REST API client with realistic error handling.
    
    Simulates:
    - Bearer token authentication
    - Role-based access control
    - Contract locking
    - Rate limiting
    """
    
    def __init__(self, config: CLMConfig = None):
        self.config = config or _config
        self._request_count = 0
        self._rate_limit = 100  # requests per minute
    
    def _check_auth(self) -> None:
        """Validate authentication."""
        if not self.config.credentials.is_valid:
            raise CLMAuthenticationError("Invalid API key")
        
        if self.config.credentials.is_token_expired():
            raise CLMAuthenticationError("API token has expired")
        
        ERROR_SIMULATOR.maybe_raise_error("clm")
    
    def _check_permission(self, permission: str) -> None:
        """Check if user has required permission."""
        if not self.config.credentials.has_permission(permission):
            raise CLMAuthorizationError(
                resource="contract",
                action=permission.split(".")[-1]
            )
    
    def _make_request(
        self,
        method: str,
        endpoint: str,
        permission: str = "contracts.read"
    ) -> None:
        """Make authenticated request with validation."""
        self._request_count += 1
        request_id = str(uuid.uuid4())[:8]
        
        log_event(
            "clm.api.request",
            method=method,
            endpoint=endpoint,
            request_id=request_id,
        )
        
        self._check_auth()
        self._check_permission(permission)
    
    def get_contract(self, contract_id: str) -> Dict[str, Any]:
        """
        GET /api/v1/contracts/{id}
        
        Retrieve contract by ID.
        """
        # Check for error simulation
        contract = MOCK_CLM_DB.get(contract_id)
        if contract and contract.get("_simulate_error"):
            self._raise_simulated_error(contract["_simulate_error"], contract_id)
        
        self._make_request("GET", f"/contracts/{contract_id}")
        
        if not contract:
            raise CLMNotFoundError("Contract", contract_id)
        
        log_event(
            "clm.api.get_contract.success",
            contract_id=contract_id,
            status=contract.get("status"),
        )
        
        return contract
    
    def get_contract_by_account(self, account_id: str) -> Optional[Dict[str, Any]]:
        """
        GET /api/v1/contracts?external_id={account_id}
        
        Search for contract by external account ID.
        """
        self._make_request("GET", f"/contracts?external_id={account_id}")
        
        contract = MOCK_CLM_DB.get(account_id)
        
        # Check for error simulation
        if contract and contract.get("_simulate_error"):
            self._raise_simulated_error(contract["_simulate_error"], account_id)
        
        return contract
    
    def get_signatories(self, contract_id: str) -> List[Dict[str, Any]]:
        """
        GET /api/v1/contracts/{id}/signatories
        
        Get signatory status for a contract.
        """
        self._make_request("GET", f"/contracts/{contract_id}/signatories", "signatories.read")
        
        contract = MOCK_CLM_DB.get(contract_id)
        if not contract:
            raise CLMNotFoundError("Contract", contract_id)
        
        return contract.get("signatories", [])
    
    def send_reminder(self, contract_id: str, signatory_id: str) -> Dict[str, Any]:
        """
        POST /api/v1/contracts/{id}/signatories/{sig_id}/remind
        
        Send signature reminder to a signatory.
        """
        self._make_request("POST", f"/contracts/{contract_id}/signatories/{signatory_id}/remind", "contracts.write")
        
        log_event(
            "clm.api.send_reminder",
            contract_id=contract_id,
            signatory_id=signatory_id,
        )
        
        return {
            "success": True,
            "message": "Reminder sent successfully",
            "timestamp": datetime.utcnow().isoformat(),
        }
    
    def _raise_simulated_error(self, error_type: str, contract_id: str) -> None:
        """Raise simulated error for testing."""
        if error_type == "authentication":
            raise CLMAuthenticationError("Invalid or expired API key")
        elif error_type == "authorization":
            raise CLMAuthorizationError("contract", "read")
        elif error_type == "server":
            raise CLMServerError("Service temporarily unavailable")
        elif error_type == "locked":
            raise CLMContractLockedError(contract_id, "another_user@company.com")


# ============================================================================
# SINGLETON CLIENT
# ============================================================================

_client: Optional[CLMClient] = None


def get_client() -> CLMClient:
    """Get or create the CLM client singleton."""
    global _client
    if _client is None:
        _client = CLMClient()
    return _client


# ============================================================================
# HIGH-LEVEL FUNCTIONS (Used by the agent)
# ============================================================================

def get_contract(account_id: str) -> Dict[str, Any]:
    """
    Fetch contract data for an account.
    
    Returns a simplified structure for the agent.
    """
    client = get_client()
    
    try:
        contract = client.get_contract_by_account(account_id)
        
        if not contract:
            return {
                "contract_id": None,
                "status": "NOT_FOUND",
                "error": f"No contract found for account {account_id}"
            }
        
        return _transform_contract_for_agent(contract)
    
    except CLMAuthenticationError as e:
        log_event("clm.api.auth_error", error=str(e), account_id=account_id)
        return {
            "contract_id": None,
            "status": "AUTH_ERROR",
            "error": str(e),
            "error_code": e.error_code,
            "http_status": e.status_code,
            "system": "CLM",
        }
    
    except CLMAuthorizationError as e:
        log_event("clm.api.permission_error", error=str(e), account_id=account_id)
        return {
            "contract_id": None,
            "status": "PERMISSION_ERROR",
            "error": str(e),
            "error_code": e.error_code,
            "http_status": e.status_code,
            "system": "CLM",
        }
    
    except CLMRateLimitError as e:
        log_event("clm.api.rate_limit_error", error=str(e), account_id=account_id)
        return {
            "contract_id": None,
            "status": "RATE_LIMIT_ERROR",
            "error": str(e),
            "error_code": e.error_code,
            "http_status": e.status_code,
            "system": "CLM",
        }
    
    except CLMValidationError as e:
        log_event("clm.api.validation_error", error=str(e), account_id=account_id)
        return {
            "contract_id": None,
            "status": "VALIDATION_ERROR",
            "error": str(e),
            "error_code": e.error_code,
            "http_status": e.status_code,
            "system": "CLM",
        }
    
    except CLMServerError as e:
        log_event("clm.api.server_error", error=str(e), account_id=account_id)
        return {
            "contract_id": None,
            "status": "SERVER_ERROR",
            "error": str(e),
            "error_code": getattr(e, 'error_code', 'INTERNAL_ERROR'),
            "http_status": e.status_code,
            "system": "CLM",
        }
    
    except CLMError as e:
        log_event("clm.api.error", error=str(e), account_id=account_id)
        return {
            "contract_id": None,
            "status": "API_ERROR",
            "error": str(e),
            "error_code": getattr(e, 'error_code', 'CLM_ERROR'),
            "http_status": getattr(e, 'status_code', 500),
            "system": "CLM",
        }
    
    except APIError as e:
        # Catch simulated errors from ERROR_SIMULATOR
        log_event("clm.api.simulated_error", error=str(e), account_id=account_id, category=str(e.category))
        status_map = {
            ErrorCategory.AUTHENTICATION: "AUTH_ERROR",
            ErrorCategory.AUTHORIZATION: "PERMISSION_ERROR",
            ErrorCategory.VALIDATION: "VALIDATION_ERROR",
            ErrorCategory.RATE_LIMIT: "RATE_LIMIT_ERROR",
            ErrorCategory.SERVER_ERROR: "SERVER_ERROR",
        }
        return {
            "contract_id": None,
            "status": status_map.get(e.category, "API_ERROR"),
            "error": str(e),
            "error_code": e.error_code,
            "http_status": e.status_code,
            "system": "CLM",
        }


def _transform_contract_for_agent(contract: Dict[str, Any]) -> Dict[str, Any]:
    """Transform CLM contract to agent-friendly format."""
    signatories = contract.get("signatories", [])
    pending_signatories = [s for s in signatories if not s.get("signed")]
    
    return {
        "contract_id": contract.get("contract_id"),
        "name": contract.get("name"),
        "status": contract.get("status"),
        "status_label": contract.get("status_details", {}).get("label"),
        "created_date": contract.get("created_date"),
        "sent_date": contract.get("sent_date"),
        "signed_date": contract.get("signed_date"),
        "effective_date": contract.get("effective_date"),
        "expiry_date": contract.get("expiry_date"),
        "signatories": signatories,
        "pending_signatories": pending_signatories,
        "all_signed": len(pending_signatories) == 0 and len(signatories) > 0,
        "key_terms": contract.get("key_terms", {}),
    }


def get_contract_status(account_id: str) -> str:
    """Get just the contract status."""
    contract = get_contract(account_id)
    return contract.get("status", "UNKNOWN")


def get_pending_signatories(account_id: str) -> List[Dict[str, Any]]:
    """Get list of signatories who haven't signed yet."""
    contract = get_contract(account_id)
    return contract.get("pending_signatories", [])


def is_fully_executed(account_id: str) -> bool:
    """Check if contract is fully executed."""
    contract = get_contract(account_id)
    return contract.get("status") == "EXECUTED"

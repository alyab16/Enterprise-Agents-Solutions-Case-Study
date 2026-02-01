"""
Shared API error types and utilities for all integrations.

This module provides:
- Standard error classes matching real API error responses
- Error simulation utilities for testing
- Authentication and permission checking
"""

from enum import Enum
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import random


# ============================================================================
# ERROR TYPES
# ============================================================================

class ErrorCategory(Enum):
    """Categories of API errors."""
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    VALIDATION = "validation"
    NOT_FOUND = "not_found"
    RATE_LIMIT = "rate_limit"
    SERVER_ERROR = "server_error"
    NETWORK = "network"


@dataclass
class APIError(Exception):
    """Base class for all API errors."""
    status_code: int
    error_code: str
    message: str
    category: ErrorCategory
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    request_id: Optional[str] = None
    
    def __str__(self):
        return f"[{self.error_code}] {self.message} (HTTP {self.status_code})"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "status_code": self.status_code,
            "error_code": self.error_code,
            "message": self.message,
            "category": self.category.value,
            "details": self.details,
            "timestamp": self.timestamp,
            "request_id": self.request_id,
        }


# ============================================================================
# SALESFORCE-SPECIFIC ERRORS
# ============================================================================

class SalesforceError(APIError):
    """Salesforce API error."""
    pass


class SalesforceAuthenticationError(SalesforceError):
    """Invalid session or expired token."""
    def __init__(self, message: str = "Session expired or invalid", details: Dict = None):
        super().__init__(
            status_code=401,
            error_code="INVALID_SESSION_ID",
            message=message,
            category=ErrorCategory.AUTHENTICATION,
            details=details or {"error": "Session expired or invalid. Please re-authenticate."}
        )


class SalesforceAuthorizationError(SalesforceError):
    """User lacks permission to access resource."""
    def __init__(self, resource: str, operation: str, details: Dict = None):
        super().__init__(
            status_code=403,
            error_code="INSUFFICIENT_ACCESS",
            message=f"Insufficient privileges to {operation} {resource}",
            category=ErrorCategory.AUTHORIZATION,
            details=details or {
                "resource": resource,
                "operation": operation,
                "required_permission": f"{resource}_{operation}".upper(),
            }
        )


class SalesforceValidationError(SalesforceError):
    """Field validation failed."""
    def __init__(self, field: str, value: Any, reason: str, details: Dict = None):
        super().__init__(
            status_code=400,
            error_code="FIELD_CUSTOM_VALIDATION_EXCEPTION",
            message=f"Validation failed for field '{field}': {reason}",
            category=ErrorCategory.VALIDATION,
            details=details or {
                "field": field,
                "value": str(value),
                "reason": reason,
                "fields": [field],
            }
        )


class SalesforceRequiredFieldError(SalesforceError):
    """Required field is missing."""
    def __init__(self, field: str, object_type: str):
        super().__init__(
            status_code=400,
            error_code="REQUIRED_FIELD_MISSING",
            message=f"Required field missing: {object_type}.{field}",
            category=ErrorCategory.VALIDATION,
            details={
                "field": field,
                "object_type": object_type,
                "fields": [field],
            }
        )


class SalesforceNotFoundError(SalesforceError):
    """Record not found."""
    def __init__(self, object_type: str, record_id: str):
        super().__init__(
            status_code=404,
            error_code="NOT_FOUND",
            message=f"{object_type} with ID '{record_id}' not found",
            category=ErrorCategory.NOT_FOUND,
            details={
                "object_type": object_type,
                "record_id": record_id,
            }
        )


class SalesforceRateLimitError(SalesforceError):
    """API rate limit exceeded."""
    def __init__(self, limit: int, reset_time: int):
        super().__init__(
            status_code=429,
            error_code="REQUEST_LIMIT_EXCEEDED",
            message=f"API rate limit exceeded. Limit: {limit} requests per 24 hours.",
            category=ErrorCategory.RATE_LIMIT,
            details={
                "limit": limit,
                "reset_in_seconds": reset_time,
                "reset_at": (datetime.utcnow() + timedelta(seconds=reset_time)).isoformat(),
            }
        )


class SalesforceServerError(SalesforceError):
    """Salesforce server error."""
    def __init__(self, message: str = "An unexpected error occurred"):
        super().__init__(
            status_code=500,
            error_code="SERVER_ERROR",
            message=message,
            category=ErrorCategory.SERVER_ERROR,
            details={"support_url": "https://help.salesforce.com/"}
        )


# ============================================================================
# NETSUITE-SPECIFIC ERRORS
# ============================================================================

class NetSuiteError(APIError):
    """NetSuite API error."""
    pass


class NetSuiteAuthenticationError(NetSuiteError):
    """Invalid credentials or token."""
    def __init__(self, message: str = "Invalid login credentials", details: Dict = None):
        super().__init__(
            status_code=401,
            error_code="INVALID_LOGIN",
            message=message,
            category=ErrorCategory.AUTHENTICATION,
            details=details or {
                "error": "Invalid login credentials. Check your token-based authentication settings.",
                "o:errorCode": "INVALID_LOGIN"
            }
        )


class NetSuiteTokenExpiredError(NetSuiteError):
    """OAuth token has expired."""
    def __init__(self):
        super().__init__(
            status_code=401,
            error_code="TOKEN_EXPIRED",
            message="OAuth token has expired. Please refresh the token.",
            category=ErrorCategory.AUTHENTICATION,
            details={
                "error": "token_expired",
                "error_description": "The access token has expired"
            }
        )


class NetSuiteAuthorizationError(NetSuiteError):
    """User lacks permission."""
    def __init__(self, permission: str, record_type: str, details: Dict = None):
        super().__init__(
            status_code=403,
            error_code="INSUFFICIENT_PERMISSION",
            message=f"You do not have permission to {permission} {record_type} records",
            category=ErrorCategory.AUTHORIZATION,
            details=details or {
                "o:errorCode": "INSUFFICIENT_PERMISSION",
                "permission_required": permission,
                "record_type": record_type,
            }
        )


class NetSuiteValidationError(NetSuiteError):
    """Field validation failed."""
    def __init__(self, field: str, value: Any, reason: str, details: Dict = None):
        super().__init__(
            status_code=400,
            error_code="INVALID_FIELD_VALUE",
            message=f"Invalid value for field '{field}': {reason}",
            category=ErrorCategory.VALIDATION,
            details=details or {
                "o:errorCode": "INVALID_FIELD_VALUE",
                "o:errorDetails": [{
                    "field": field,
                    "value": str(value),
                    "reason": reason,
                }]
            }
        )


class NetSuiteRequiredFieldError(NetSuiteError):
    """Required field is missing."""
    def __init__(self, field: str, record_type: str):
        super().__init__(
            status_code=400,
            error_code="MISSING_REQD_FIELD",
            message=f"Please enter a value for {field}",
            category=ErrorCategory.VALIDATION,
            details={
                "o:errorCode": "MISSING_REQD_FIELD",
                "field": field,
                "record_type": record_type,
            }
        )


class NetSuiteNotFoundError(NetSuiteError):
    """Record not found."""
    def __init__(self, record_type: str, record_id: str):
        super().__init__(
            status_code=404,
            error_code="RCRD_DSNT_EXIST",
            message=f"That record does not exist.",
            category=ErrorCategory.NOT_FOUND,
            details={
                "o:errorCode": "RCRD_DSNT_EXIST",
                "record_type": record_type,
                "record_id": record_id,
            }
        )


class NetSuiteRateLimitError(NetSuiteError):
    """Concurrency limit exceeded."""
    def __init__(self, limit: int):
        super().__init__(
            status_code=429,
            error_code="EXCEEDED_CONCURRENCY_LIMIT",
            message=f"Request limit exceeded. Maximum concurrent requests: {limit}",
            category=ErrorCategory.RATE_LIMIT,
            details={
                "o:errorCode": "EXCEEDED_CONCURRENCY_LIMIT",
                "limit": limit,
            }
        )


class NetSuiteServerError(NetSuiteError):
    """NetSuite server error."""
    def __init__(self, message: str = "An unexpected error has occurred"):
        super().__init__(
            status_code=500,
            error_code="UNEXPECTED_ERROR",
            message=message,
            category=ErrorCategory.SERVER_ERROR,
            details={
                "o:errorCode": "UNEXPECTED_ERROR",
                "support_url": "https://system.netsuite.com/app/support/supportcenter.nl"
            }
        )


# ============================================================================
# API CREDENTIALS AND SESSION MANAGEMENT
# ============================================================================

@dataclass
class APICredentials:
    """Simulated API credentials."""
    client_id: str
    client_secret: str
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_expiry: Optional[datetime] = None
    is_valid: bool = True
    permissions: List[str] = field(default_factory=list)
    
    def is_token_expired(self) -> bool:
        if self.token_expiry is None:
            return False
        return datetime.utcnow() > self.token_expiry
    
    def has_permission(self, permission: str) -> bool:
        return permission in self.permissions or "*" in self.permissions


# Default credentials for simulation
SALESFORCE_CREDENTIALS = APICredentials(
    client_id="3MVG9...mock",
    client_secret="mock_secret",
    access_token="00D...mock_token",
    token_expiry=datetime.utcnow() + timedelta(hours=2),
    is_valid=True,
    permissions=["Account.read", "Account.write", "Opportunity.read", "Contract.read", "User.read"]
)

NETSUITE_CREDENTIALS = APICredentials(
    client_id="mock_consumer_key",
    client_secret="mock_consumer_secret",
    access_token="mock_token_id",
    refresh_token="mock_token_secret",
    token_expiry=datetime.utcnow() + timedelta(hours=1),
    is_valid=True,
    permissions=["invoice.read", "invoice.create", "customer.read"]
)


# ============================================================================
# ERROR SIMULATION UTILITIES
# ============================================================================

class ErrorSimulator:
    """
    Utility to simulate random API errors for testing.
    
    Can be configured to inject errors at a certain rate.
    """
    
    def __init__(
        self,
        auth_error_rate: float = 0.0,
        validation_error_rate: float = 0.0,
        rate_limit_error_rate: float = 0.0,
        server_error_rate: float = 0.0,
        enabled: bool = False
    ):
        self.auth_error_rate = auth_error_rate
        self.validation_error_rate = validation_error_rate
        self.rate_limit_error_rate = rate_limit_error_rate
        self.server_error_rate = server_error_rate
        self.enabled = enabled

    def maybe_raise_error(self, api_type: str = "salesforce") -> None:
        if not self.enabled:
            return

        # One roll across buckets
        roll = random.random()
        thresholds = [
            ("auth", self.auth_error_rate),
            ("validation", self.validation_error_rate),
            ("rate_limit", self.rate_limit_error_rate),
            ("server", self.server_error_rate),
        ]

        cumulative = 0.0
        chosen = None
        for name, rate in thresholds:
            cumulative += max(0.0, rate)
            if roll < cumulative:
                chosen = name
                break
        if not chosen:
            return

        # Raise the appropriate error based on api_type
        if chosen == "auth":
            if api_type == "salesforce":
                raise SalesforceAuthenticationError()
            elif api_type == "netsuite":
                raise NetSuiteAuthenticationError()
            else:
                # For CLM and other types, raise a generic APIError that can be caught
                raise APIError(
                    status_code=401,
                    error_code="AUTHENTICATION_ERROR",
                    message=f"Simulated {api_type} authentication error",
                    category=ErrorCategory.AUTHENTICATION
                )

        if chosen == "server":
            if api_type == "salesforce":
                raise SalesforceServerError("Temporary service disruption")
            elif api_type == "netsuite":
                raise NetSuiteServerError("Temporary service disruption")
            else:
                raise APIError(
                    status_code=500,
                    error_code="SERVER_ERROR",
                    message=f"Simulated {api_type} server error",
                    category=ErrorCategory.SERVER_ERROR
                )

        if chosen == "rate_limit":
            if api_type == "salesforce":
                raise SalesforceRateLimitError(
                    limit=100000,
                    reset_time=3600
                )
            elif api_type == "netsuite":
                raise NetSuiteRateLimitError(limit=10)
            else:
                raise APIError(
                    status_code=429,
                    error_code="RATE_LIMIT",
                    message=f"Simulated {api_type} rate limit error",
                    category=ErrorCategory.RATE_LIMIT
                )

        if chosen == "validation":
            if api_type == "salesforce":
                raise SalesforceValidationError(
                    field="Name", value=None, reason="Simulated validation failure"
                )
            elif api_type == "netsuite":
                raise NetSuiteValidationError(
                    field="entity", value="INVALID", reason="Simulated validation failure"
                )
            else:
                raise APIError(
                    status_code=400,
                    error_code="VALIDATION_ERROR",
                    message=f"Simulated {api_type} validation error",
                    category=ErrorCategory.VALIDATION
                )


# Global error simulator (disabled by default)
ERROR_SIMULATOR = ErrorSimulator(enabled=False)


def enable_error_simulation(
    auth_rate: float = 0.05,
    validation_rate: float = 0.05,
    rate_limit_rate: float = 0.02,
    server_error_rate: float = 0.01
):
    """Enable random error simulation for testing.
    
    IMPORTANT: We modify the existing ERROR_SIMULATOR object in-place
    rather than replacing it, because other modules have already imported
    a reference to it at module load time.
    """
    ERROR_SIMULATOR.auth_error_rate = auth_rate
    ERROR_SIMULATOR.validation_error_rate = validation_rate
    ERROR_SIMULATOR.rate_limit_error_rate = rate_limit_rate
    ERROR_SIMULATOR.server_error_rate = server_error_rate
    ERROR_SIMULATOR.enabled = True


def disable_error_simulation():
    """Disable error simulation."""
    ERROR_SIMULATOR.enabled = False


# ============================================================================
# VALIDATION UTILITIES
# ============================================================================

def validate_salesforce_credentials(credentials: APICredentials) -> None:
    """Validate Salesforce credentials before making API calls."""
    if not credentials.is_valid:
        raise SalesforceAuthenticationError(
            message="Invalid credentials. Please check your connected app settings."
        )
    
    if credentials.is_token_expired():
        raise SalesforceAuthenticationError(
            message="Session has expired. Please re-authenticate.",
            details={"expired_at": credentials.token_expiry.isoformat()}
        )


def validate_netsuite_credentials(credentials: APICredentials) -> None:
    """Validate NetSuite credentials before making API calls."""
    if not credentials.is_valid:
        raise NetSuiteAuthenticationError(
            message="Invalid token-based authentication credentials."
        )
    
    if credentials.is_token_expired():
        raise NetSuiteTokenExpiredError()


def check_salesforce_permission(credentials: APICredentials, object_type: str, operation: str) -> None:
    """Check if user has permission for the operation."""
    permission = f"{object_type}.{operation}"
    if not credentials.has_permission(permission):
        raise SalesforceAuthorizationError(
            resource=object_type,
            operation=operation
        )


def check_netsuite_permission(credentials: APICredentials, record_type: str, operation: str) -> None:
    """Check if user has permission for the operation."""
    permission = f"{record_type}.{operation}"
    if not credentials.has_permission(permission):
        raise NetSuiteAuthorizationError(
            permission=operation,
            record_type=record_type
        )

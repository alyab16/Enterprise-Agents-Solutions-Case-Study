"""
Mock Salesforce REST API integration with realistic error handling.

This simulates the actual Salesforce REST API structure:
- GET /services/data/vXX.0/sobjects/Account/{id}
- GET /services/data/vXX.0/sobjects/Opportunity/{id}
- GET /services/data/vXX.0/sobjects/Contract/{id}
- GET /services/data/vXX.0/sobjects/User/{id}
- POST /services/data/vXX.0/sobjects/{object}
- PATCH /services/data/vXX.0/sobjects/{object}/{id}

In production, this would use:
- OAuth 2.0 authentication (Web Server Flow or JWT Bearer)
- simple-salesforce SDK or requests library
- Base URL: https://{instance}.salesforce.com/services/data/v59.0
"""

import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from app.logging.logger import log_event
from app.integrations.api_errors import (
    SalesforceError,
    SalesforceAuthenticationError,
    SalesforceAuthorizationError,
    SalesforceValidationError,
    SalesforceRequiredFieldError,
    SalesforceNotFoundError,
    SalesforceRateLimitError,
    SalesforceServerError,
    APICredentials,
    SALESFORCE_CREDENTIALS,
    validate_salesforce_credentials,
    check_salesforce_permission,
    ERROR_SIMULATOR,
)


# ============================================================================
# API CONFIGURATION
# ============================================================================

@dataclass
class SalesforceConfig:
    """Salesforce API configuration."""
    instance_url: str = "https://stackadapt.my.salesforce.com"
    api_version: str = "v59.0"
    credentials: APICredentials = None
    
    def __post_init__(self):
        if self.credentials is None:
            self.credentials = SALESFORCE_CREDENTIALS
    
    @property
    def base_url(self) -> str:
        return f"{self.instance_url}/services/data/{self.api_version}"


# Global config
_config = SalesforceConfig()


# ============================================================================
# MOCK DATA
# ============================================================================

MOCK_ACCOUNTS = {
    "ACME-001": {
        "Id": "0018Z00003ACMEQ",
        "Name": "ACME Corp",
        "BillingCountry": "United States",
        "BillingCity": "San Francisco",
        "BillingState": "CA",
        "BillingStreet": "123 Enterprise Ave",
        "BillingPostalCode": "94105",
        "Industry": "Technology",
        "OwnerId": "0058Z000001OWNER",
        "IsDeleted": False,
        "Website": "https://acme.com",
        "NumberOfEmployees": 500,
        "AnnualRevenue": 50000000,
        "Type": "Customer",
        "CreatedDate": "2023-06-15T10:30:00.000+0000",
        "LastModifiedDate": "2024-01-15T14:30:00.000+0000",
        "attributes": {
            "type": "Account",
            "url": "/services/data/v59.0/sobjects/Account/0018Z00003ACMEQ"
        }
    },
    "BETA-002": {
        "Id": "0018Z00003BETAQ",
        "Name": "Beta Industries",
        "BillingCountry": "Canada",
        "BillingCity": "Toronto",
        "BillingState": "ON",
        "Industry": "Manufacturing",
        "OwnerId": "0058Z000001OWNER",
        "IsDeleted": False,
        "Type": "Prospect",
        "attributes": {
            "type": "Account",
            "url": "/services/data/v59.0/sobjects/Account/0018Z00003BETAQ"
        }
    },
    "GAMMA-003": {
        "Id": "0018Z00003GAMMAQ",
        "Name": "Gamma Startup",
        # Missing BillingCountry - will trigger warning
        "Industry": "Fintech",
        "OwnerId": "0058Z000001OWNER",
        "IsDeleted": False,
        "Type": "Customer",
        "attributes": {
            "type": "Account",
            "url": "/services/data/v59.0/sobjects/Account/0018Z00003GAMMAQ"
        }
    },
    "DELETED-004": {
        "Id": "0018Z00003DELTAQ",
        "Name": "Deleted Corp",
        "IsDeleted": True,  # Will trigger violation
        "attributes": {
            "type": "Account",
            "url": "/services/data/v59.0/sobjects/Account/0018Z00003DELTAQ"
        }
    },
    # Special error simulation accounts
    "AUTH-ERROR": {
        "_simulate_error": "authentication",
    },
    "PERM-ERROR": {
        "_simulate_error": "authorization",
    },
    "SERVER-ERROR": {
        "_simulate_error": "server",
    },
}

MOCK_USERS = {
    "0058Z000001OWNER": {
        "Id": "0058Z000001OWNER",
        "Username": "cs.manager@stackadapt.demo",
        "Email": "cs.manager@stackadapt.demo",
        "FirstName": "Sarah",
        "LastName": "Johnson",
        "Name": "Sarah Johnson",
        "Title": "Customer Success Manager",
        "Department": "Customer Success",
        "IsActive": True,
        "ProfileId": "00e8Z000001PROFILE",
        "Profile": {"Name": "Standard User"},
        "TimeZoneSidKey": "America/New_York",
        "LocaleSidKey": "en_US",
        "ManagerId": "0058Z000001MANAGER",
        "attributes": {
            "type": "User",
            "url": "/services/data/v59.0/sobjects/User/0058Z000001OWNER"
        }
    },
    "INACTIVE-USER": {
        "Id": "INACTIVE-USER",
        "Username": "inactive@stackadapt.demo",
        "Email": "inactive@stackadapt.demo",
        "Name": "Inactive User",
        "IsActive": False,  # Will trigger violation
        "ProfileId": "00e8Z000001PROFILE",
        "attributes": {
            "type": "User",
            "url": "/services/data/v59.0/sobjects/User/INACTIVE-USER"
        }
    },
}

MOCK_OPPORTUNITIES = {
    "OPP-ACME-001": {
        "Id": "0068Z000001OPPACME",
        "Name": "ACME Corp - Enterprise Deal",
        "AccountId": "0018Z00003ACMEQ",
        "StageName": "Closed Won",
        "Amount": 150000.00,
        "CloseDate": "2024-01-15",
        "OwnerId": "0058Z000001OWNER",
        "ContractId": "8008Z000000CONTR",
        "IsClosed": True,
        "IsWon": True,
        "Probability": 100,
        "Type": "New Business",
        "LeadSource": "Website",
        "attributes": {
            "type": "Opportunity",
            "url": "/services/data/v59.0/sobjects/Opportunity/0068Z000001OPPACME"
        }
    },
    "OPP-BETA-002": {
        "Id": "0068Z000001OPPBETA",
        "Name": "Beta Industries - Growth Plan",
        "AccountId": "0018Z00003BETAQ",
        "StageName": "Negotiation",  # Not won yet - will trigger violation
        "Amount": 75000.00,
        "CloseDate": "2024-02-28",
        "OwnerId": "0058Z000001OWNER",
        "IsClosed": False,
        "IsWon": False,
        "Probability": 60,
        "attributes": {
            "type": "Opportunity",
            "url": "/services/data/v59.0/sobjects/Opportunity/0068Z000001OPPBETA"
        }
    },
    "OPP-GAMMA-003": {
        "Id": "0068Z000001OPPGAMMA",
        "Name": "Gamma Startup - Pilot",
        "AccountId": "0018Z00003GAMMAQ",
        "StageName": "Closed Won",
        "Amount": 25000.00,
        "CloseDate": "2024-01-20",
        "OwnerId": "0058Z000001OWNER",
        "IsClosed": True,
        "IsWon": True,
        # Missing ContractId - will trigger warning
        "attributes": {
            "type": "Opportunity",
            "url": "/services/data/v59.0/sobjects/Opportunity/0068Z000001OPPGAMMA"
        }
    },
}

MOCK_CONTRACTS = {
    "8008Z000000CONTR": {
        "Id": "8008Z000000CONTR",
        "ContractNumber": "00000123",
        "AccountId": "0018Z00003ACMEQ",
        "OwnerId": "0058Z000001OWNER",
        "Status": "Activated",
        "StartDate": "2024-01-01",
        "EndDate": "2024-12-31",
        "ActivatedDate": "2024-01-01T10:00:00.000+0000",
        "CustomerSignedDate": "2023-12-20",
        "CompanySignedDate": "2023-12-21",
        "ContractTerm": 12,
        "attributes": {
            "type": "Contract",
            "url": "/services/data/v59.0/sobjects/Contract/8008Z000000CONTR"
        }
    },
    "CONTRACT-DRAFT": {
        "Id": "CONTRACT-DRAFT",
        "ContractNumber": "00000124",
        "AccountId": "0018Z00003BETAQ",
        "OwnerId": "0058Z000001OWNER",
        "Status": "Draft",  # Will trigger warning
        "StartDate": "2024-02-01",
        "ContractTerm": 12,
        "attributes": {
            "type": "Contract",
            "url": "/services/data/v59.0/sobjects/Contract/CONTRACT-DRAFT"
        }
    },
    "CONTRACT-PENDING": {
        "Id": "CONTRACT-PENDING",
        "ContractNumber": "00000125",
        "AccountId": "0018Z00003GAMMAQ",
        "Status": "In Approval Process",  # Will trigger warning
        "StartDate": "2024-02-01",
        # Missing OwnerId - will trigger warning
        "attributes": {
            "type": "Contract",
            "url": "/services/data/v59.0/sobjects/Contract/CONTRACT-PENDING"
        }
    },
}


# ============================================================================
# SALESFORCE API CLIENT
# ============================================================================

class SalesforceClient:
    """
    Mock Salesforce REST API client with realistic error handling.
    
    Simulates:
    - OAuth authentication
    - Permission checking
    - Field validation
    - Error responses matching real Salesforce API
    """
    
    def __init__(self, config: SalesforceConfig = None):
        self.config = config or _config
        self._request_count = 0
        self._daily_request_count = 0
        self._daily_limit = 100000  # Salesforce daily API limit
    
    def _check_auth(self) -> None:
        """Validate authentication before making requests."""
        validate_salesforce_credentials(self.config.credentials)
        ERROR_SIMULATOR.maybe_raise_error("salesforce")
    
    def _check_permission(self, object_type: str, operation: str) -> None:
        """Check if user has permission for the operation."""
        check_salesforce_permission(self.config.credentials, object_type, operation)
    
    def _check_rate_limit(self) -> None:
        """Check if we've exceeded rate limits."""
        self._daily_request_count += 1
        if self._daily_request_count > self._daily_limit:
            raise SalesforceRateLimitError(
                limit=self._daily_limit,
                reset_time=86400  # 24 hours
            )
    
    def _make_request(
        self,
        method: str,
        endpoint: str,
        object_type: str,
        operation: str = "read",
        json_body: Dict = None,
    ) -> Dict[str, Any]:
        """Make a request to Salesforce API with full validation."""
        self._request_count += 1
        request_id = str(uuid.uuid4())[:8]
        
        log_event(
            "salesforce.api.request",
            method=method,
            endpoint=endpoint,
            object_type=object_type,
            request_id=request_id,
        )
        
        # Validate auth, permissions, and rate limits
        self._check_auth()
        self._check_permission(object_type, operation)
        self._check_rate_limit()
        
        return {"request_id": request_id}
    
    def get_account(self, account_id: str) -> Dict[str, Any]:
        """
        GET /services/data/v59.0/sobjects/Account/{id}
        
        Retrieve an account by ID.
        """
        # Check for error simulation
        account = MOCK_ACCOUNTS.get(account_id)
        if account and account.get("_simulate_error"):
            self._raise_simulated_error(account["_simulate_error"], "Account", account_id)
        
        self._make_request("GET", f"/sobjects/Account/{account_id}", "Account", "read")
        
        if not account:
            raise SalesforceNotFoundError("Account", account_id)
        
        log_event(
            "salesforce.api.get_account.success",
            account_id=account_id,
            account_name=account.get("Name"),
        )
        
        return account
    
    def get_user(self, user_id: str) -> Dict[str, Any]:
        """
        GET /services/data/v59.0/sobjects/User/{id}
        
        Retrieve a user by ID.
        """
        self._make_request("GET", f"/sobjects/User/{user_id}", "User", "read")
        
        user = MOCK_USERS.get(user_id)
        if not user:
            raise SalesforceNotFoundError("User", user_id)
        
        return user
    
    def get_opportunity(self, opportunity_id: str) -> Dict[str, Any]:
        """
        GET /services/data/v59.0/sobjects/Opportunity/{id}
        
        Retrieve an opportunity by ID.
        """
        self._make_request("GET", f"/sobjects/Opportunity/{opportunity_id}", "Opportunity", "read")
        
        opp = MOCK_OPPORTUNITIES.get(opportunity_id)
        if not opp:
            raise SalesforceNotFoundError("Opportunity", opportunity_id)
        
        return opp
    
    def get_contract(self, contract_id: str) -> Dict[str, Any]:
        """
        GET /services/data/v59.0/sobjects/Contract/{id}
        
        Retrieve a contract by ID.
        """
        self._make_request("GET", f"/sobjects/Contract/{contract_id}", "Contract", "read")
        
        contract = MOCK_CONTRACTS.get(contract_id)
        if not contract:
            raise SalesforceNotFoundError("Contract", contract_id)
        
        return contract
    
    def query(self, soql: str) -> Dict[str, Any]:
        """
        GET /services/data/v59.0/query?q={soql}
        
        Execute a SOQL query.
        """
        self._make_request("GET", "/query", "Query", "read")
        
        log_event("salesforce.api.query", soql=soql)
        
        # Simple query parsing for demo
        # In production, would use actual SOQL parser
        return {
            "totalSize": 0,
            "done": True,
            "records": []
        }
    
    def create_record(self, object_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        POST /services/data/v59.0/sobjects/{object}
        
        Create a new record.
        """
        self._make_request("POST", f"/sobjects/{object_type}", object_type, "write")
        
        # Validate required fields
        self._validate_create_data(object_type, data)
        
        new_id = f"mock_{uuid.uuid4().hex[:15]}"
        
        log_event(
            "salesforce.api.create_record",
            object_type=object_type,
            new_id=new_id,
        )
        
        return {
            "id": new_id,
            "success": True,
            "errors": []
        }
    
    def update_record(self, object_type: str, record_id: str, data: Dict[str, Any]) -> None:
        """
        PATCH /services/data/v59.0/sobjects/{object}/{id}
        
        Update an existing record.
        """
        self._make_request("PATCH", f"/sobjects/{object_type}/{record_id}", object_type, "write")
        
        # Validate field values
        self._validate_update_data(object_type, data)
        
        log_event(
            "salesforce.api.update_record",
            object_type=object_type,
            record_id=record_id,
            fields=list(data.keys()),
        )
    
    def _validate_create_data(self, object_type: str, data: Dict[str, Any]) -> None:
        """Validate data for create operations."""
        required_fields = {
            "Account": ["Name"],
            "Opportunity": ["Name", "StageName", "CloseDate"],
            "Contract": ["AccountId", "Status", "StartDate"],
        }
        
        for field in required_fields.get(object_type, []):
            if field not in data or data[field] is None:
                raise SalesforceRequiredFieldError(field, object_type)
    
    def _validate_update_data(self, object_type: str, data: Dict[str, Any]) -> None:
        """Validate data for update operations."""
        # Validate specific field values
        if object_type == "Opportunity":
            if "StageName" in data:
                valid_stages = ["Prospecting", "Qualification", "Needs Analysis", 
                               "Value Proposition", "Negotiation", "Closed Won", "Closed Lost"]
                if data["StageName"] not in valid_stages:
                    raise SalesforceValidationError(
                        field="StageName",
                        value=data["StageName"],
                        reason=f"Invalid picklist value. Valid values are: {', '.join(valid_stages)}"
                    )
            
            if "Amount" in data and data["Amount"] is not None:
                if not isinstance(data["Amount"], (int, float)) or data["Amount"] < 0:
                    raise SalesforceValidationError(
                        field="Amount",
                        value=data["Amount"],
                        reason="Amount must be a non-negative number"
                    )
        
        if object_type == "Contract":
            if "Status" in data:
                valid_statuses = ["Draft", "In Approval Process", "Activated"]
                if data["Status"] not in valid_statuses:
                    raise SalesforceValidationError(
                        field="Status",
                        value=data["Status"],
                        reason=f"Invalid status. Valid values are: {', '.join(valid_statuses)}"
                    )
    
    def _raise_simulated_error(self, error_type: str, object_type: str, record_id: str) -> None:
        """Raise a simulated error for testing."""
        if error_type == "authentication":
            raise SalesforceAuthenticationError(
                message="Session expired or invalid. Please re-authenticate."
            )
        elif error_type == "authorization":
            raise SalesforceAuthorizationError(
                resource=object_type,
                operation="read"
            )
        elif error_type == "server":
            raise SalesforceServerError(
                message="Service temporarily unavailable. Please try again later."
            )


# ============================================================================
# SINGLETON CLIENT
# ============================================================================

_client: Optional[SalesforceClient] = None


def get_client() -> SalesforceClient:
    """Get or create the Salesforce client singleton."""
    global _client
    if _client is None:
        _client = SalesforceClient()
    return _client


# ============================================================================
# HIGH-LEVEL FUNCTIONS (Used by the agent)
# ============================================================================

def get_account(account_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetch account data from Salesforce.
    
    Returns None if not found, raises exception on other errors.
    """
    client = get_client()
    
    try:
        return client.get_account(account_id)
    except SalesforceNotFoundError:
        log_event("salesforce.account.not_found", account_id=account_id)
        return None
    except SalesforceError as e:
        log_event("salesforce.account.error", account_id=account_id, error=str(e))
        # For the agent, we return None on errors but log them
        # In production, you might want to re-raise or handle differently
        return None


def get_user(user_id: str) -> Optional[Dict[str, Any]]:
    """Fetch user data from Salesforce."""
    client = get_client()
    
    try:
        return client.get_user(user_id)
    except SalesforceNotFoundError:
        return None
    except SalesforceError as e:
        log_event("salesforce.user.error", user_id=user_id, error=str(e))
        return None


def get_opportunity(opportunity_id: str) -> Optional[Dict[str, Any]]:
    """Fetch opportunity data from Salesforce."""
    client = get_client()
    
    try:
        return client.get_opportunity(opportunity_id)
    except SalesforceNotFoundError:
        return None
    except SalesforceError as e:
        log_event("salesforce.opportunity.error", opportunity_id=opportunity_id, error=str(e))
        return None


def get_opportunity_by_account(account_id: str) -> Optional[Dict[str, Any]]:
    """Fetch opportunity by account ID."""
    account = MOCK_ACCOUNTS.get(account_id, {})
    sf_account_id = account.get("Id") if not account.get("_simulate_error") else None
    
    if not sf_account_id:
        return None
    
    for opp in MOCK_OPPORTUNITIES.values():
        if opp.get("AccountId") == sf_account_id:
            return opp
    return None


def get_contract(contract_id: str) -> Optional[Dict[str, Any]]:
    """Fetch contract data from Salesforce."""
    client = get_client()
    
    try:
        return client.get_contract(contract_id)
    except SalesforceNotFoundError:
        return None
    except SalesforceError as e:
        log_event("salesforce.contract.error", contract_id=contract_id, error=str(e))
        return None


def get_contract_by_account(account_id: str) -> Optional[Dict[str, Any]]:
    """Fetch contract by account ID."""
    account = MOCK_ACCOUNTS.get(account_id, {})
    sf_account_id = account.get("Id") if not account.get("_simulate_error") else None
    
    if not sf_account_id:
        return None
    
    for contract in MOCK_CONTRACTS.values():
        if contract.get("AccountId") == sf_account_id:
            return contract
    return None


# ============================================================================
# ERROR SIMULATION HELPERS
# ============================================================================

def simulate_auth_error():
    """Force an authentication error on next request."""
    _config.credentials.is_valid = False


def simulate_expired_token():
    """Force a token expiration error."""
    _config.credentials.token_expiry = datetime.utcnow() - timedelta(hours=1)


def reset_credentials():
    """Reset credentials to valid state."""
    global _config
    _config = SalesforceConfig()

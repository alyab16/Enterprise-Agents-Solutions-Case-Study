"""
Mock Salesforce integration for demo purposes.
In production, this would use the Salesforce REST API or simple-salesforce SDK.
"""

MOCK_ACCOUNTS = {
    "ACME-001": {
        "Id": "0018Z00003ACMEQ",
        "Name": "ACME Corp",
        "BillingCountry": "United States",
        "BillingCity": "San Francisco",
        "Industry": "Technology",
        "OwnerId": "0058Z000001OWNER",
        "IsDeleted": False,
        "Website": "https://acme.com",
        "NumberOfEmployees": 500,
    },
    "BETA-002": {
        "Id": "0018Z00003BETAQ",
        "Name": "Beta Industries",
        "BillingCountry": "Canada",
        "BillingCity": "Toronto",
        "Industry": "Manufacturing",
        "OwnerId": "0058Z000001OWNER",
        "IsDeleted": False,
    },
    "GAMMA-003": {
        "Id": "0018Z00003GAMMAQ",
        "Name": "Gamma Startup",
        # Missing BillingCountry - will trigger warning
        "Industry": "Fintech",
        "OwnerId": "0058Z000001OWNER",
        "IsDeleted": False,
    },
    "DELETED-004": {
        "Id": "0018Z00003DELTAQ",
        "Name": "Deleted Corp",
        "IsDeleted": True,  # Will trigger violation
    },
}

MOCK_USERS = {
    "0058Z000001OWNER": {
        "Id": "0058Z000001OWNER",
        "Username": "cs.manager@stackadapt.demo",
        "Email": "cs.manager@stackadapt.demo",
        "FirstName": "Sarah",
        "LastName": "Johnson",
        "Title": "Customer Success Manager",
        "Department": "Customer Success",
        "IsActive": True,
        "ProfileId": "00e8Z000001PROFILE",
        "TimeZoneSidKey": "America/New_York",
        "LocaleSidKey": "en_US",
        "ManagerId": "0058Z000001MANAGER",
    },
    "INACTIVE-USER": {
        "Id": "INACTIVE-USER",
        "Username": "inactive@stackadapt.demo",
        "Email": "inactive@stackadapt.demo",
        "IsActive": False,  # Will trigger violation
        "ProfileId": "00e8Z000001PROFILE",
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
    },
    "OPP-BETA-002": {
        "Id": "0068Z000001OPPBETA",
        "Name": "Beta Industries - Growth Plan",
        "AccountId": "0018Z00003BETAQ",
        "StageName": "Negotiation",  # Not won yet - will trigger violation
        "Amount": 75000.00,
        "CloseDate": "2024-02-28",
        "OwnerId": "0058Z000001OWNER",
    },
    "OPP-GAMMA-003": {
        "Id": "0068Z000001OPPGAMMA",
        "Name": "Gamma Startup - Pilot",
        "AccountId": "0018Z00003GAMMAQ",
        "StageName": "Closed Won",
        "Amount": 25000.00,
        "CloseDate": "2024-01-20",
        "OwnerId": "0058Z000001OWNER",
        # Missing ContractId - will trigger warning
    },
}

MOCK_CONTRACTS = {
    "8008Z000000CONTR": {
        "Id": "8008Z000000CONTR",
        "AccountId": "0018Z00003ACMEQ",
        "OwnerId": "0058Z000001OWNER",
        "Status": "Activated",
        "StartDate": "2024-01-01",
        "EndDate": "2024-12-31",
        "ActivatedDate": "2024-01-01T10:00:00Z",
        "CustomerSignedDate": "2023-12-20",
        "ContractTerm": 12,
    },
    "CONTRACT-DRAFT": {
        "Id": "CONTRACT-DRAFT",
        "AccountId": "0018Z00003BETAQ",
        "OwnerId": "0058Z000001OWNER",
        "Status": "Draft",  # Will trigger warning
        "StartDate": "2024-02-01",
        "ContractTerm": 12,
    },
    "CONTRACT-PENDING": {
        "Id": "CONTRACT-PENDING",
        "AccountId": "0018Z00003GAMMAQ",
        "Status": "In Approval Process",  # Will trigger warning
        "StartDate": "2024-02-01",
        # Missing OwnerId - will trigger warning
    },
}


def get_account(account_id: str) -> dict | None:
    """Fetch account data from Salesforce."""
    return MOCK_ACCOUNTS.get(account_id)


def get_user(user_id: str) -> dict | None:
    """Fetch user data from Salesforce."""
    return MOCK_USERS.get(user_id)


def get_opportunity(opportunity_id: str) -> dict | None:
    """Fetch opportunity data from Salesforce."""
    return MOCK_OPPORTUNITIES.get(opportunity_id)


def get_opportunity_by_account(account_id: str) -> dict | None:
    """Fetch opportunity by account ID."""
    sf_account_id = MOCK_ACCOUNTS.get(account_id, {}).get("Id")
    for opp in MOCK_OPPORTUNITIES.values():
        if opp.get("AccountId") == sf_account_id:
            return opp
    return None


def get_contract(contract_id: str) -> dict | None:
    """Fetch contract data from Salesforce."""
    return MOCK_CONTRACTS.get(contract_id)


def get_contract_by_account(account_id: str) -> dict | None:
    """Fetch contract by account ID."""
    sf_account_id = MOCK_ACCOUNTS.get(account_id, {}).get("Id")
    for contract in MOCK_CONTRACTS.values():
        if contract.get("AccountId") == sf_account_id:
            return contract
    return None

from typing import TypedDict, Dict, List, Any, Optional


class APIErrorInfo(TypedDict, total=False):
    """Structured information about an API error."""
    system: str  # salesforce, netsuite, clm, provisioning
    error_type: str  # authentication, authorization, validation, server, rate_limit
    error_code: str  # INVALID_SESSION_ID, INSUFFICIENT_PERMISSION, etc.
    message: str  # Human-readable error message
    http_status: int  # 401, 403, 500, etc.
    timestamp: str
    details: Dict[str, Any]  # Additional error details
    resolution: str  # How to fix this error


class AgentState(TypedDict, total=False):
    # Metadata
    account_id: str
    correlation_id: str
    event_type: str
    
    # Domain data from integrations
    account: Dict[str, Any]
    opportunity: Dict[str, Any]
    contract: Dict[str, Any]
    user: Dict[str, Any]
    invoice: Dict[str, Any]
    clm: Dict[str, Any]  # CLM contract data
    provisioning: Dict[str, Any]

    # API Errors - captures details about any integration failures
    api_errors: List[APIErrorInfo]

    # Governance & validation
    violations: Dict[str, List[str]]
    warnings: Dict[str, List[str]]
    decisions: List[str]
    overrides: Dict[str, str]
    
    # Control flow
    stage: str
    decision: str
    
    # Risk analysis (LLM-powered)
    risk_analysis: Dict[str, Any]
    
    # Actions taken
    actions_taken: List[Dict[str, Any]]
    notifications_sent: List[Dict[str, Any]]
    
    # Human-readable outputs
    human_summary: str
    recommended_actions: List[str]

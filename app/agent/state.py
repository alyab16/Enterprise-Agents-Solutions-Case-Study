from typing import TypedDict, Dict, List, Any, Optional


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
    provisioning: Dict[str, Any]

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

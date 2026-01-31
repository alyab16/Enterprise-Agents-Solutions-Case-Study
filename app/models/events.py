"""
Pydantic models for API events and responses.
"""

import uuid
from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any


class TriggerEvent(BaseModel):
    """Event that triggers the onboarding workflow."""
    event_type: str = Field(
        ..., 
        examples=["opportunity.closed_won", "manual.trigger"],
        description="Type of event that triggered the onboarding"
    )
    account_id: str = Field(
        ..., 
        examples=["ACME-001", "BETA-002"],
        description="Account ID to onboard"
    )
    correlation_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique ID for tracking this onboarding run"
    )


class OnboardingResponse(BaseModel):
    """Response from the onboarding webhook."""
    correlation_id: str
    account_id: str
    decision: str
    stage: str
    risk_level: Optional[str] = None
    summary: Optional[str] = None
    violations: Dict[str, List[str]] = Field(default_factory=dict)
    warnings: Dict[str, List[str]] = Field(default_factory=dict)
    actions_taken: List[Dict[str, Any]] = Field(default_factory=list)
    notifications_sent: List[Dict[str, Any]] = Field(default_factory=list)
    recommended_actions: List[str] = Field(default_factory=list)
    provisioning: Optional[Dict[str, Any]] = None


class DebugPayload(BaseModel):
    """Payload for debug endpoint with mock data."""
    account: Optional[Dict[str, Any]] = None
    user: Optional[Dict[str, Any]] = None
    contract: Optional[Dict[str, Any]] = None
    opportunity: Optional[Dict[str, Any]] = None
    invoice: Optional[Dict[str, Any]] = None

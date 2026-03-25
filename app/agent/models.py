"""
Pydantic models for the onboarding agent's structured output.

The agent returns an OnboardingResult as its final answer after
reasoning through the tool calls. Pydantic AI validates this
output automatically.
"""

from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Any, Dict, List, Literal, Optional


class RecommendedAction(BaseModel):
    """A recommended action for resolving an issue."""
    action: str
    owner: str = "Customer Success"
    priority: int = 1


class OnboardingResult(BaseModel):
    """
    Structured output from the onboarding agent.

    The LLM must produce this exact schema as its final response.
    Pydantic AI validates and retries if the schema doesn't match.
    """

    decision: Literal["PROCEED", "ESCALATE", "BLOCK"]
    risk_level: Literal["low", "medium", "high", "critical"]
    summary: str = Field(description="Human-readable 1-3 sentence summary of the onboarding status")

    violations: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Blocking issues grouped by domain (e.g. 'salesforce', 'contract')",
    )
    warnings: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Non-blocking concerns grouped by domain",
    )
    api_errors: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="API integration errors encountered during data fetching",
    )

    recommended_actions: List[RecommendedAction] = Field(
        default_factory=list,
        description="Ordered list of actions to resolve identified issues",
    )
    actions_taken: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Actions the agent performed (provision, notify, etc.)",
    )
    notifications_sent: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Notifications dispatched by the agent",
    )
    provisioning: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Provisioning details if decision is PROCEED",
    )

    # Raw data collected during the run (for report generation)
    account_data: Optional[Dict[str, Any]] = Field(default=None, exclude=True)
    user_data: Optional[Dict[str, Any]] = Field(default=None, exclude=True)
    opportunity_data: Optional[Dict[str, Any]] = Field(default=None, exclude=True)
    contract_data: Optional[Dict[str, Any]] = Field(default=None, exclude=True)
    clm_data: Optional[Dict[str, Any]] = Field(default=None, exclude=True)
    invoice_data: Optional[Dict[str, Any]] = Field(default=None, exclude=True)

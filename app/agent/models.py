"""
Pydantic models for the onboarding agent's structured output.

The agent returns an OnboardingResult as its final answer after
reasoning through the tool calls. Pydantic AI validates this
output automatically.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator
from typing import Any, Dict, List, Literal, Optional, Union


class RecommendedAction(BaseModel):
    """A recommended action for resolving an issue."""
    action: str
    owner: str = "Customer Success"
    priority: int = 1


def _flatten_to_strings(v: Any) -> List[str]:
    """Recursively extract all string values from nested dicts/lists."""
    if isinstance(v, str):
        return [v]
    if isinstance(v, list):
        out: List[str] = []
        for item in v:
            out.extend(_flatten_to_strings(item))
        return out
    if isinstance(v, dict):
        out = []
        for val in v.values():
            out.extend(_flatten_to_strings(val))
        return out
    return [str(v)]


class OnboardingResult(BaseModel):
    """
    Structured output from the onboarding agent.

    The LLM must produce this exact schema as its final response.
    Pydantic AI validates and retries if the schema doesn't match.
    """

    decision: Literal["PROCEED", "ESCALATE", "BLOCK"]
    risk_level: Literal["low", "medium", "high", "critical"]
    summary: str = Field(description="Human-readable 1-3 sentence summary of the onboarding status")

    violations: Union[Dict[str, List[str]], List[Any]] = Field(
        default_factory=dict,
        description="Blocking issues grouped by domain (e.g. 'salesforce', 'contract')",
    )
    warnings: Union[Dict[str, List[str]], List[Any]] = Field(
        default_factory=dict,
        description="Non-blocking concerns grouped by domain",
    )

    @field_validator("violations", "warnings", mode="before")
    @classmethod
    def _normalize_to_dict(cls, v: Any) -> Dict[str, List[str]]:
        """Accept any shape from the LLM and normalize to Dict[str, List[str]].

        gpt-4o-mini returns violations/warnings in many shapes:
        - List of strings or dicts
        - Dict[str, List[str]]  (correct)
        - Dict[str, Dict[str, ...]]  (nested — needs flattening)
        - Dict[str, str]  (single values instead of lists)
        """
        if isinstance(v, list):
            items = []
            for item in v:
                if isinstance(item, str):
                    items.append(item)
                elif isinstance(item, dict):
                    items.extend(_flatten_to_strings(item))
                else:
                    items.append(str(item))
            return {"general": items} if items else {}
        if isinstance(v, dict):
            result: Dict[str, List[str]] = {}
            for key, val in v.items():
                if isinstance(val, list) and all(isinstance(s, str) for s in val):
                    result[str(key)] = val
                else:
                    result[str(key)] = _flatten_to_strings(val)
            return result
        return {}
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

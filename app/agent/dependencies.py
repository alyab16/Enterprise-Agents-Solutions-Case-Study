"""
Dependency injection for the Pydantic AI onboarding agent.

Dependencies carry runtime context that tools need to operate:
- account_id: which account is being onboarded
- correlation_id: tracking ID for observability
- event_type: what triggered this onboarding run
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class OnboardingDeps:
    """Runtime dependencies injected into the onboarding agent."""

    account_id: str
    correlation_id: str = ""
    event_type: str = "manual"

    # Collected data — populated by fetch tools, used by validate tool
    collected_account: Optional[dict] = field(default=None, repr=False)
    collected_user: Optional[dict] = field(default=None, repr=False)
    collected_opportunity: Optional[dict] = field(default=None, repr=False)
    collected_contract: Optional[dict] = field(default=None, repr=False)
    collected_clm: Optional[dict] = field(default=None, repr=False)
    collected_invoice: Optional[dict] = field(default=None, repr=False)

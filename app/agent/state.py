from typing import Any, Dict, Literal, TypedDict

OnboardingStage = Literal[
    "START",
    "WAITING_FOR_CONTRACT",
    "WAITING_FOR_INVOICE",
    "READY_TO_PROVISION",
    "PROVISIONING",
    "ACTIVE",
    "BLOCKED",
]


class AgentState(TypedDict, total=False):
    correlation_id: str
    account_id: str
    trigger_event_type: str

    salesforce: Dict[str, Any]
    clm: Dict[str, Any]
    netsuite: Dict[str, Any]
    provisioning: Dict[str, Any]

    stage: OnboardingStage
    risks: list[str]
    actions_taken: list[str]
    human_summary: str

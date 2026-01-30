import uuid
from pydantic import BaseModel, Field


class TriggerEvent(BaseModel):
    event_type: str = Field(..., examples=["opportunity.closed_won"])
    account_id: str = Field(..., examples=["ACME-001"])
    correlation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))

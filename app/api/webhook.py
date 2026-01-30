from fastapi import APIRouter
from app.agent.graph import build_graph
from app.models.events import TriggerEvent

router = APIRouter()
graph = build_graph()


@router.post("/webhook/onboarding")
async def onboarding_webhook(evt: TriggerEvent):
    state = {
        "account_id": evt.account_id,
        "correlation_id": evt.correlation_id,
        "trigger_event_type": evt.event_type,
    }
    return graph.invoke(state)

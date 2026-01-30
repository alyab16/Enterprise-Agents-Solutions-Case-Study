import json
import os
from app.agent.state import AgentState
from app.logging.logger import log_event

try:
    from openai import OpenAI
except Exception:
    OpenAI = None


def generate_summary(state: AgentState) -> str:
    fallback = (
        f"Account {state['account_id']} onboarding status:\n"
        f"- Stage: {state.get('stage')}\n"
        f"- Risks: {', '.join(state.get('risks', [])) or 'None'}\n"
        f"- Actions: {', '.join(state.get('actions_taken', [])) or 'None'}"
    )

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or OpenAI is None:
        return fallback

    try:
        client = OpenAI(api_key=api_key)
        resp = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": "Summarize onboarding status for CS."},
                {"role": "user", "content": json.dumps(state, indent=2)},
            ],
            temperature=0.2,
            store=True,
            metadata={
                "project": "onboarding-agent",
                "account_id": state.get("account_id"),
                "correlation_id": state.get("correlation_id"),
                "agent_step": "generate_summary",
            },
        )

        return resp.choices[0].message.content.strip()
    except Exception as e:
        log_event("llm.error", error=str(e))
        return fallback

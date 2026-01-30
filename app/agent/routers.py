from app.agent.state import AgentState


def after_contract(state: AgentState) -> str:
    if state.get("stage") == "WAITING_FOR_CONTRACT":
        return "generate_summary"
    return "check_invoice"


def after_invoice(state: AgentState) -> str:
    if state.get("stage") == "WAITING_FOR_INVOICE":
        return "generate_summary"
    return "provision"

from app.agent.state import AgentState
from app.integrations import salesforce, clm, netsuite, provisioning
from app.llm.summary import generate_summary
from app.logging.logger import log_event


def init_node(state: AgentState) -> AgentState:
    state["stage"] = "START"
    state["risks"] = []
    state["actions_taken"] = []
    return state


def fetch_salesforce(state: AgentState) -> AgentState:
    sf = salesforce.get_account(state["account_id"])
    state["salesforce"] = sf
    log_event("salesforce.fetched", account_id=state["account_id"])
    return state


def check_contract(state: AgentState) -> AgentState:
    contract = clm.get_contract(state["account_id"])
    state["clm"] = contract

    if contract["status"] != "EXECUTED":
        state["stage"] = "WAITING_FOR_CONTRACT"
        state["risks"].append("Contract not executed")

    return state


def check_invoice(state: AgentState) -> AgentState:
    invoice = netsuite.get_invoice(state["account_id"])
    state["netsuite"] = invoice

    if invoice["status"] != "PAID":
        state["stage"] = "WAITING_FOR_INVOICE"
        state["risks"].append("Invoice not paid")
    else:
        state["stage"] = "READY_TO_PROVISION"

    return state


def provision_account(state: AgentState) -> AgentState:
    if state.get("stage") != "READY_TO_PROVISION":
        return state

    state["stage"] = "PROVISIONING"
    prov = provisioning.provision(state["account_id"])
    state["provisioning"] = prov
    state["actions_taken"].append(f"Provisioned tenant {prov['tenant_id']}")
    state["stage"] = "ACTIVE"
    return state


def generate_summary_node(state: AgentState) -> AgentState:
    state["human_summary"] = generate_summary(state)
    return state

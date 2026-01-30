from langgraph.graph import StateGraph, END
from app.agent.state import AgentState
from app.agent import nodes, routers


def build_graph():
    g = StateGraph(AgentState)

    g.add_node("init", nodes.init_node)
    g.add_node("fetch_salesforce", nodes.fetch_salesforce)
    g.add_node("check_contract", nodes.check_contract)
    g.add_node("check_invoice", nodes.check_invoice)
    g.add_node("provision", nodes.provision_account)
    g.add_node("generate_summary", nodes.generate_summary_node)

    g.set_entry_point("init")
    g.add_edge("init", "fetch_salesforce")
    g.add_edge("fetch_salesforce", "check_contract")

    g.add_conditional_edges(
        "check_contract",
        routers.after_contract,
        {
            "check_invoice": "check_invoice",
            "generate_summary": "generate_summary",
        },
    )

    g.add_conditional_edges(
        "check_invoice",
        routers.after_invoice,
        {
            "provision": "provision",
            "generate_summary": "generate_summary",
        },
    )

    g.add_edge("provision", "generate_summary")
    g.add_edge("generate_summary", END)

    return g.compile()

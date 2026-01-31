"""
LangGraph-based agent graph for customer onboarding.

This graph orchestrates the entire onboarding workflow:
1. Initialize state
2. Fetch data from Salesforce, CLM, NetSuite
3. Validate data against business rules
4. Analyze risks using LLM
5. Make routing decision (BLOCK/ESCALATE/PROCEED)
6. Send notifications or provision account
7. Generate summary
"""

from langgraph.graph import StateGraph, END
from app.agent.state import AgentState
from app.agent import nodes, router


def build_graph() -> StateGraph:
    """
    Build and compile the onboarding agent graph.
    
    Graph structure:
    
    init → fetch_salesforce → fetch_clm → fetch_invoice → validate
                                                              ↓
                                                        analyze_risks
                                                              ↓
                                                        make_decision
                                                        ↓           ↓
                              (BLOCK/ESCALATE)→ send_notifications   provision ←(PROCEED)
                                                        ↓           ↓
                                                    generate_summary
                                                              ↓
                                                            END
    """
    
    # Create the graph with AgentState
    graph = StateGraph(AgentState)
    
    # ----------------------------
    # Add nodes
    # ----------------------------
    graph.add_node("init", nodes.init_node)
    graph.add_node("fetch_salesforce", nodes.fetch_salesforce_data)
    graph.add_node("fetch_clm", nodes.fetch_clm_data)
    graph.add_node("fetch_invoice", nodes.fetch_invoice_data)
    graph.add_node("validate", nodes.validate_data)
    graph.add_node("analyze_risks", nodes.analyze_risks_node)
    graph.add_node("make_decision", nodes.make_decision)
    graph.add_node("send_notifications", nodes.send_notifications)
    graph.add_node("provision", nodes.provision_account)
    graph.add_node("generate_summary", nodes.generate_summary_node)
    
    # ----------------------------
    # Add edges (linear flow through data fetching)
    # ----------------------------
    graph.set_entry_point("init")
    
    graph.add_edge("init", "fetch_salesforce")
    graph.add_edge("fetch_salesforce", "fetch_clm")
    graph.add_edge("fetch_clm", "fetch_invoice")
    graph.add_edge("fetch_invoice", "validate")
    graph.add_edge("validate", "analyze_risks")
    graph.add_edge("analyze_risks", "make_decision")
    
    # ----------------------------
    # Conditional edges based on decision
    # ----------------------------
    graph.add_conditional_edges(
        "make_decision",
        router.after_decision,
        {
            "send_notifications": "send_notifications",
            "provision": "provision",
        }
    )
    
    # Both paths converge to generate_summary
    graph.add_edge("send_notifications", "generate_summary")
    graph.add_edge("provision", "generate_summary")
    
    # End after summary
    graph.add_edge("generate_summary", END)
    
    return graph.compile()


# Pre-compiled graph instance for reuse
_compiled_graph = None


def get_graph():
    """Get or create the compiled graph (singleton pattern)."""
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph()
    return _compiled_graph


def run_onboarding(account_id: str, correlation_id: str = None, event_type: str = None) -> AgentState:
    """
    Run the onboarding workflow for an account.
    
    Args:
        account_id: The account to onboard
        correlation_id: Optional tracking ID
        event_type: Optional event type that triggered this run
        
    Returns:
        Final AgentState with all results
    """
    from app.agent.state_utils import init_state
    import uuid
    
    # Initialize state
    initial_state = init_state(
        account_id=account_id,
        correlation_id=correlation_id or str(uuid.uuid4()),
        event_type=event_type or "manual",
    )
    
    # Get compiled graph
    graph = get_graph()
    
    # Run the graph
    final_state = graph.invoke(initial_state)
    
    return final_state

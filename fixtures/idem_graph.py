"""Approval node + execute node that passes a deterministic idempotency key to the provider."""
from langgraph.graph import StateGraph, START, END
from fixtures import payments, safe_graph
def execute(s):
    if not s.get("approved"): return {}
    return {"charge_id": payments.charge(s["amount"], idempotency_key=f"order-{s['amount']}")}
def build(cp):
    g = StateGraph(safe_graph.S); g.add_node("approve", safe_graph.approve); g.add_node("execute", execute)
    g.add_edge(START, "approve"); g.add_edge("approve", "execute"); g.add_edge("execute", END)
    return g.compile(checkpointer=cp)

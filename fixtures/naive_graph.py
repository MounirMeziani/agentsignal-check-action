"""Charges BEFORE interrupt() in the same node: re-runs on resume -> double charge."""
from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.types import interrupt
from fixtures import payments
class S(TypedDict, total=False):
    amount: int; charge_id: str; ok: bool
def pay(s):
    cid = payments.charge(s["amount"])
    ok = interrupt({"q": "confirm receipt?"})
    return {"charge_id": cid, "ok": ok}
def build(cp):
    g = StateGraph(S); g.add_node("pay", pay); g.add_edge(START, "pay"); g.add_edge("pay", END)
    return g.compile(checkpointer=cp)

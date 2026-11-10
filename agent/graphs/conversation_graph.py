"""Conversation graph (one thread per client conversation): liaison -> approval (interrupt) -> send."""
from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from agent.graphs.bid_graph import guarded
from agent.nodes.client_liaison import liaison_node, reply_approval_node, send_node
from agent.state import ConversationState


def build_conversation_graph(checkpointer=None, store=None):
    g = StateGraph(ConversationState)
    g.add_node("client_liaison", guarded("client_liaison", liaison_node))
    g.add_node("approval", reply_approval_node)
    g.add_node("send", guarded("send", send_node))
    g.add_edge(START, "client_liaison")
    g.add_conditional_edges("client_liaison", lambda s: "approval" if s.get("status") == "awaiting_approval" else END,
                            ["approval", END])
    g.add_conditional_edges("approval", lambda s: "send" if s["status"] == "approved" else END, ["send", END])
    g.add_edge("send", END)
    return g.compile(checkpointer=checkpointer, store=store)

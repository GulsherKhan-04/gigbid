"""Renders both graphs from code into docs/images/*.mmd (Mermaid) for the README and report."""
import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from pathlib import Path

from agent.graphs.bid_graph import build_bid_graph
from agent.graphs.conversation_graph import build_conversation_graph

out = Path(__file__).resolve().parents[1] / "docs" / "images"
out.mkdir(parents=True, exist_ok=True)
for name, g in [("bid_graph", build_bid_graph()), ("conversation_graph", build_conversation_graph())]:
    (out / f"{name}.mmd").write_text(g.get_graph().draw_mermaid())
    print("wrote", out / f"{name}.mmd")

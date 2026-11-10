"""R&D question C: (a) one ReAct agent with all tools, (b) prebuilt langgraph-supervisor, (c) our hand-built graph.

    python -m evals.runners.multiagent_compare --limit 50

Same jobs, same models (from agent/config.yaml), same claim checker and compliance rules for every system.
Writes evals/results/multiagent_compare.json. Uses the dev set; falls back to data/sample/jobs.json for a dry run.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import re
import time
import uuid

from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.prebuilt import create_react_agent
from langgraph.store.memory import InMemoryStore
from langgraph_supervisor import create_supervisor

from agent.graphs.bid_graph import build_bid_graph
from agent.llm import LLM
from agent.mcp_client import connections, hub
from agent.nodes.compliance import rule_check
from agent.settings import config, prompt
from evals.runners.common import ROOT, load_dev, mean, pct, save
from rag.retriever import retrieve
from rag.verify import unsupported_rate, verify_claims

READ_TOOLS = {"search_jobs", "get_job", "get_client_history", "get_connects_balance", "search_evidence",
              "get_case_study", "list_skills"}


def chat(node: str) -> ChatOpenAI:
    llm = LLM()
    return ChatOpenAI(model=llm.model_for(node), base_url=llm.base_url, api_key=llm.api_key, temperature=0.2,
                      max_retries=6)


def parse(text: str) -> dict:
    m = re.search(r"\{.*\}", text or "", re.S)
    try:
        return json.loads(m.group(0)) if m else {}
    except json.JSONDecodeError:
        return {}


def tokens_of(messages) -> int:
    return sum((getattr(m, "usage_metadata", None) or {}).get("total_tokens", 0) for m in messages)


async def run_single(tools, job, persona, user="eval"):
    agent = create_react_agent(chat("writer"), tools)
    p = prompt("baseline_single_agent").replace("{user}", user).replace("{job_id}", job["job_id"]).replace(
        "{max_words}", str(config()["policy"]["max_proposal_words"]))
    out = await agent.ainvoke({"messages": [("system", p), ("user", f"Analyse job {job['job_id']} for persona {persona}.")]},
                              {"recursion_limit": 30})
    return parse(out["messages"][-1].content), tokens_of(out["messages"])


async def run_supervisor(tools, job, persona, user="eval"):
    by = {t.name: t for t in tools}
    researcher = create_react_agent(chat("analyst"), [by[n] for n in READ_TOOLS if n in by], name="researcher")
    writer = create_react_agent(chat("writer"), [by[n] for n in ("search_evidence", "get_case_study") if n in by],
                                name="writer")
    p = prompt("baseline_supervisor").replace("{user}", user).replace("{job_id}", job["job_id"])
    app = create_supervisor([researcher, writer], model=chat("critic"), prompt=p).compile()
    out = await app.ainvoke({"messages": [("user", f"Analyse job {job['job_id']} for persona {persona}.")]},
                            {"recursion_limit": 40})
    return parse(out["messages"][-1].content), tokens_of(out["messages"])


async def run_graph(job, persona):
    g = build_bid_graph(InMemorySaver(), InMemoryStore())
    s = await g.ainvoke({"user_id": "eval", "persona": persona, "profile": {}, "job": job},
                        {"configurable": {"thread_id": f"cmp-{uuid.uuid4().hex}"}})
    d = s.get("decision") or {}
    usage = s.get("usage", {})
    return ({"action": d.get("action"), "reason": d.get("reason"), "price_usd": (s.get("price_quote") or {}).get("amount_usd"),
             "proposal": (s.get("proposal_draft") or {}).get("cover_letter")},
            sum(u.get("prompt_tokens", 0) + u.get("completion_tokens", 0) for u in usage.values()))


async def score(out: dict, job: dict, persona: str) -> dict:
    proposal = out.get("proposal")
    res = {"action": out.get("action"), "unsupported": None, "violations": None}
    if proposal:
        ev = await retrieve(persona, f"{job.get('title', '')}. {job.get('description', '')}", [], 8,
                            config()["rag"]["variant"])
        claims, _ = await verify_claims(proposal, ev)
        res["unsupported"] = unsupported_rate(claims)
        res["violations"] = len(rule_check(proposal)[1])
    return res


async def main(limit: int | None):
    rows = load_dev(limit=limit)
    if not rows:
        rows = [{"persona": None, "job": j, "action": None, "job_type": "sample"}
                for j in json.loads((ROOT / "data/sample/jobs.json").read_text())]
        print("No dev set found: dry run on sample jobs (no accuracy can be computed).")
    client = MultiServerMCPClient(connections())
    tools = [t for t in await client.get_tools() if t.name in READ_TOOLS]
    from rag.retriever import personas
    systems = {"single_react": run_single, "supervisor": run_supervisor}
    results = {k: [] for k in ("single_react", "supervisor", "graph")}
    for r in rows:
        persona = r["persona"] or personas()[0]
        job = {**r["job"], "job_id": r["job"].get("job_id") or uuid.uuid4().hex[:8]}
        for name in ("single_react", "supervisor", "graph"):
            t0 = time.monotonic()
            try:
                out, tok = await (run_graph(job, persona) if name == "graph" else systems[name](tools, job, persona))
                err = None
            except Exception as e:  # noqa: BLE001  a crash counts against the system, it is not skipped
                out, tok, err = {}, 0, f"{type(e).__name__}: {e}"[:200]
            try:
                sc = await score(out, job, persona)
            except Exception as e:  # noqa: BLE001
                sc = {"action": out.get("action"), "unsupported": None, "violations": None}
                err = err or f"scoring failed: {e}"[:200]
            results[name].append({**sc, "gold": r["action"], "job_type": r["job_type"], "tokens": tok,
                                  "seconds": round(time.monotonic() - t0, 2), "error": err})
    summary = {}
    for name, rs in results.items():
        labelled = [x for x in rs if x["gold"]]
        summary[name] = {
            "n": len(rs), "accuracy": mean(float(x["action"] == x["gold"]) for x in labelled) if labelled else None,
            "unsupported_rate": mean(x["unsupported"] for x in rs), "compliance_violations_in_output": sum(x["violations"] or 0 for x in rs),
            "tokens_per_job": mean(x["tokens"] for x in rs), "p50_s": pct([x["seconds"] for x in rs], .5),
            "p95_s": pct([x["seconds"] for x in rs], .95), "errors": sum(bool(x["error"]) for x in rs),
            "accuracy_by_job_type": {t: mean(float(x["action"] == x["gold"]) for x in labelled if x["job_type"] == t)
                                     for t in sorted({x["job_type"] for x in labelled})}}
    print(json.dumps(summary, indent=1))
    save("multiagent_compare", {"summary": summary, "rows": results, "dry_run": not any(r["action"] for r in rows)})
    await hub().close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=50)
    asyncio.run(main(ap.parse_args().limit))

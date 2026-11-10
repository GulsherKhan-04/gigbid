import uuid

import pytest
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.memory import InMemoryStore
from langgraph.types import Command

from agent.graphs.bid_graph import build_bid_graph
from agent.llm import set_llm
from agent.mcp_client import hub
from tests.fakes import FakeLLM

PROFILE = {"minimum_project_budget_usd": 200}


async def run(graph, job_id, thread):
    cfg = {"configurable": {"thread_id": thread}}
    return await graph.ainvoke({"user_id": "u1", "persona": "sample-ai-engineer", "profile": PROFILE,
                                "job": {"job_id": job_id}}, cfg), cfg


@pytest.mark.asyncio
async def test_good_job_reaches_approval_then_submits_once():
    fake = FakeLLM(critic_fail_times=1)
    set_llm(fake)
    g = build_bid_graph(InMemorySaver(), InMemoryStore())
    out, cfg = await run(g, "sample-job-001", str(uuid.uuid4()))
    assert "__interrupt__" in out, out.get("status")
    payload = out["__interrupt__"][0].value
    assert payload["dry_run"]["dry_run"] is True
    assert "Kaggle" not in payload["draft"]["cover_letter"]          # unsupported claim removed (B3)
    assert fake.calls.count("writer") == 2                             # one Critic loop
    assert {"analyst", "risk_assessor", "fit_matcher"} <= set(fake.calls)
    done = await g.ainvoke(Command(resume={"action": "approve"}), cfg)
    assert done["status"] == "submitted"
    again = await g.ainvoke(Command(resume={"action": "approve"}), cfg)  # replay of finished thread: no resubmit
    assert again["submission"]["idempotency_key"] == done["submission"]["idempotency_key"]
    await hub().close()


@pytest.mark.asyncio
async def test_unpaid_trial_is_skipped():
    set_llm(FakeLLM())
    g = build_bid_graph(InMemorySaver(), InMemoryStore())
    out, _ = await run(g, "sample-job-002", str(uuid.uuid4()))
    assert out["status"] == "skipped"
    assert out["decision"]["action"] == "skip"
    await hub().close()

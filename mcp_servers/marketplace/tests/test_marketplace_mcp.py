import pytest
from mcp.shared.memory import create_connected_server_and_client_session as connect

from mcp_servers.marketplace.server import mcp

P = {"user": "u-mcp", "job_id": "sample-job-001", "cover_letter": "x" * 80, "bid_amount_usd": 300,
     "connects_cost": 8, "idempotency_key": "test-key-0001"}


@pytest.mark.asyncio
async def test_dry_run_and_idempotent_writes():
    async with connect(mcp._mcp_server) as s:
        dry = (await s.call_tool("create_proposal_draft", {"p": {**P, "dry_run": True}})).structuredContent
        assert dry["dry_run"] and dry["preview"]["connects_cost"] == 8
        a = (await s.call_tool("create_proposal_draft", {"p": P})).structuredContent
        b = (await s.call_tool("create_proposal_draft", {"p": P})).structuredContent
        assert b["replayed"] and a["result"]["draft_id"] == b["result"]["draft_id"]
        bad = await s.call_tool("create_proposal_draft", {"p": {**P, "cover_letter": "too short"}})
        assert bad.isError


@pytest.mark.asyncio
async def test_annotations():
    async with connect(mcp._mcp_server) as s:
        tools = {t.name: t for t in (await s.list_tools()).tools}
        assert tools["get_job"].annotations.readOnlyHint
        assert tools["submit_proposal"].annotations.destructiveHint
        assert tools["submit_proposal"].annotations.idempotentHint

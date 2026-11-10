"""Fails CI when an MCP tool signature changes unintentionally. After an intended change run:
    UPDATE_SNAPSHOTS=1 pytest tests/contract"""
import json
import os
from pathlib import Path

import pytest
from mcp.shared.memory import create_connected_server_and_client_session as connect

from mcp_servers.marketplace.server import mcp as market
from mcp_servers.portfolio.server import mcp as portfolio
from mcp_servers.workspace.server import mcp as workspace

SNAP = Path(__file__).parent / "snapshots"


@pytest.mark.asyncio
@pytest.mark.parametrize("name,server", [("portfolio", portfolio), ("marketplace", market), ("workspace", workspace)])
async def test_schema_snapshot(name, server):
    async with connect(server._mcp_server) as s:
        tools = sorted(((await s.list_tools()).tools), key=lambda t: t.name)
    current = {t.name: {"input": t.inputSchema, "output": t.outputSchema,
                        "annotations": t.annotations.model_dump(exclude_none=True) if t.annotations else None}
               for t in tools}
    path = SNAP / f"{name}.json"
    if os.getenv("UPDATE_SNAPSHOTS") or not path.exists():
        SNAP.mkdir(exist_ok=True)
        path.write_text(json.dumps(current, indent=1, sort_keys=True))
    assert current == json.loads(path.read_text()), f"{name} tool schema changed; see docstring"

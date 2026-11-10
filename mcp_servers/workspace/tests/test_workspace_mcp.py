import pytest
from mcp.shared.memory import create_connected_server_and_client_session as connect

from mcp_servers.workspace.server import mcp


@pytest.mark.asyncio
async def test_slots():
    async with connect(mcp._mcp_server) as s:
        r = await s.call_tool("free_slots", {"days": 2})
        assert not r.isError

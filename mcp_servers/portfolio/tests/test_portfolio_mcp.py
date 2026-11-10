import pytest
from mcp.shared.memory import create_connected_server_and_client_session as connect

from mcp_servers.portfolio.server import mcp


@pytest.mark.asyncio
async def test_search_and_resources():
    async with connect(mcp._mcp_server) as s:
        r = (await s.call_tool("search_evidence", {"requirement": "scikit-learn classification", "k": 3})).structuredContent
        items = r["result"]
        assert items and {"evidence_id", "type", "source", "outcome"} <= set(items[0])
        templates = [t.uriTemplate for t in (await s.list_resource_templates()).resourceTemplates]
        assert "portfolio://case/{id}" in templates and "portfolio://proposal/{id}" in templates
        assert (await s.list_prompts()).prompts

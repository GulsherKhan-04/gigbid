"""B1: ingest repos through GitHub's official MCP server (third-party server, see docs/TOOLS.md).

    python -m rag.ingest.github --persona <name> --repos owner/repo,owner/other

Fetches each repo's README and a few code files with the `get_file_contents` tool, writes them under
data/personas/<persona>/repos/<repo>/ and re-indexes incrementally. Check tool names with MCP Inspector if
GitHub renames them. Needs GITHUB_TOKEN (read-only, public repos scope is enough).
"""
from __future__ import annotations

import argparse
import asyncio
import base64
import json
import os

from langchain_mcp_adapters.client import MultiServerMCPClient

from rag.ingest.loaders import ROOT
from rag.retriever import reindex

CODE_PATHS = ["main.py", "app.py", "src/main.py", "src/index.ts", "requirements.txt", "package.json"]


def _text(result) -> str | None:
    if result.isError:
        return None
    for c in result.content:
        t = getattr(c, "text", None)
        if t:
            try:
                d = json.loads(t)
                if isinstance(d, dict) and d.get("content"):
                    return base64.b64decode(d["content"]).decode("utf-8", "ignore")
            except (json.JSONDecodeError, ValueError):
                return t
        r = getattr(c, "resource", None)
        if r is not None and getattr(r, "text", None):
            return r.text
    return None


async def ingest(persona: str, repos: list[str]) -> int:
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        raise SystemExit("GITHUB_TOKEN is empty: paste a read-only token in .env")
    client = MultiServerMCPClient({"github": {"transport": "streamable_http",
                                              "url": os.getenv("GITHUB_MCP_URL") or "https://api.githubcopilot.com/mcp/",
                                              "headers": {"Authorization": f"Bearer {token}"}}})
    async with client.session("github") as s:
        for full in repos:
            owner, repo = full.strip().split("/", 1)
            out = ROOT / "data" / "personas" / persona / "repos" / repo
            out.mkdir(parents=True, exist_ok=True)
            for path in ["README.md"] + CODE_PATHS:
                text = _text(await s.call_tool("get_file_contents", {"owner": owner, "repo": repo, "path": path}))
                if text:
                    (out / path.replace("/", "__")).write_text(text[:20000], encoding="utf-8")
                    print("fetched", full, path)
    return reindex(persona)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--persona", required=True)
    ap.add_argument("--repos", required=True)
    a = ap.parse_args()
    print("chunks indexed:", asyncio.run(ingest(a.persona, a.repos.split(","))))

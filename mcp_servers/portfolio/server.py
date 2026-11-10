"""Portfolio MCP server (read-only). Usable from Claude Desktop or Cursor:

    uvx --from gigbid-portfolio-mcp portfolio-mcp            # after publishing
    python -m mcp_servers.portfolio.server --stdio            # from this repo
"""
from __future__ import annotations

import os
import sys
from typing import Literal

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from pydantic import BaseModel, Field

from rag.retriever import get_index, retrieve
from agent.settings import config

mcp = FastMCP("gigbid-portfolio", instructions="Search a freelancer's portfolio for evidence that proves a "
              "client requirement. Read-only. Every item has an id you can cite.")
RO = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False)
PERSONA = (os.getenv("PORTFOLIO_PERSONA") or "")


def _persona(p: str | None) -> str:
    from rag.retriever import personas
    return p or PERSONA or personas()[0]


class EvidenceItem(BaseModel):
    evidence_id: str
    type: str
    source: str
    date: str = ""
    outcome: str = ""
    project: str = ""
    title: str = ""
    skills: list[str] = Field(default_factory=list)
    text: str
    score: float = 0.0


class Filters(BaseModel):
    type: Literal["case_study", "readme", "code", "cv", "proposal", "review"] | None = None
    outcome: Literal["won", "replied", "ignored"] | None = None
    client_industry: str | None = None


@mcp.tool(annotations=RO, structured_output=True)
async def search_evidence(requirement: str = Field(min_length=3, max_length=500),
                          k: int = Field(5, ge=1, le=20), filters: Filters | None = None,
                          persona: str | None = None, requirements: list[str] | None = None,
                          variant: str | None = None) -> list[EvidenceItem]:
    """Find portfolio evidence (case studies, repos, code, reviews, past proposals) that proves a requirement."""
    f = {k2: v for k2, v in (filters.model_dump() if filters else {}).items() if v}
    hits = await retrieve(_persona(persona), requirement, requirements or [], k,
                          variant or config()["rag"]["variant"], f or None)
    return [EvidenceItem(**{x: h.get(x) for x in EvidenceItem.model_fields if x in h}) for h in hits]


@mcp.tool(annotations=RO, structured_output=True)
def get_case_study(id: str, persona: str | None = None) -> EvidenceItem:
    """Return one portfolio item in full by its evidence id."""
    idx = get_index(_persona(persona))
    if id not in idx.by_id:
        raise ValueError(f"unknown evidence id {id}")
    c = idx.by_id[id]
    return EvidenceItem(**{x: c.get(x) for x in EvidenceItem.model_fields if x in c})


@mcp.tool(annotations=RO, structured_output=True)
def list_skills(persona: str | None = None) -> dict[str, int]:
    """Skills named across the portfolio with how many items mention each."""
    counts: dict[str, int] = {}
    for c in get_index(_persona(persona)).chunks:
        for s in c.get("skills", []):
            counts[s] = counts.get(s, 0) + 1
    return dict(sorted(counts.items(), key=lambda x: -x[1]))


@mcp.resource("portfolio://case/{id}")
def case_resource(id: str) -> str:
    c = get_index(_persona(None)).by_id[id]
    return f"# {c.get('title') or c['project']}\nsource: {c['source']}\n\n{c['text']}"


@mcp.resource("portfolio://proposal/{id}")
def proposal_resource(id: str) -> str:
    c = get_index(_persona(None)).by_id[id]
    return f"Outcome: {c.get('outcome') or 'unknown'}\n\n{c['text']}"


@mcp.prompt(title="Answer a screening question from my portfolio")
def answer_screening_question(question: str) -> str:
    return (f"Answer this client screening question in under 120 words: \"{question}\". First call "
            "search_evidence with the question, then answer using only facts from the returned items and cite "
            "their ids in brackets. If nothing supports an answer, say what you would do instead of inventing it.")


@mcp.prompt(title="Prove I can do this job")
def prove_fit(job_post: str) -> str:
    return ("List each requirement in the job post below, call search_evidence for each, and build a table: "
            f"requirement | best evidence id | strength.\n\nJob post:\n{job_post}")


if __name__ == "__main__":
    if "--stdio" in sys.argv:
        mcp.run("stdio")
    else:
        import uvicorn
        from mcp_servers.auth import BearerAuth
        uvicorn.run(BearerAuth(mcp.streamable_http_app(), "PORTFOLIO_MCP_TOKEN"), host="0.0.0.0",
                    port=int((os.getenv("PORT") or 8101)))

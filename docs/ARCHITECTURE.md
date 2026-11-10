# Architecture

```
Web (React, TS) ──SSE/REST──> FastAPI ──enqueue──> Arq worker (Redis)
                                  │                    │
                                  └──── LangGraph bid graph / conversation graph ────┐
                                         Postgres checkpointer + LangGraph store      │
                                                                                      ▼
                       MCP client (per-agent allowlists, timeouts, retries, degraded mode)
                         │                    │                         │
                  Portfolio MCP        Marketplace MCP            Workspace MCP
                  (RAG variants)   (GigSim adapter | fixtures)   (calendar, email drafts)
                                         │
                              MarketplacePort ── UpworkLivePort (official Upwork MCP)
```

Rendered graphs: `docs/images/bid_graph.mmd`, `docs/images/conversation_graph.mmd` (`make graphs`).

## Why each agent exists
- **Scout**: the only node that polls the marketplace; dedupes reposts by content fingerprint.
- **Job Analyst**: turns a messy post into a typed `JobSpec` so later steps never parse prose.
- **Risk Assessor**: model judgement plus deterministic backstops (injection patterns, warning signals) the model cannot override.
- **Fit Matcher**: runs in parallel with the Analyst, so it derives its own requirement list; builds the requirement-to-evidence matrix.
- **Decision**: pure rules over typed reports and config thresholds.
- **Pricing Strategist**: deterministic: client band, market median, user floor, Connects expected value.
- **Proposal Writer**: strongest model; sees only retrieved evidence, style memory and outcome memory.
- **Verifier** (claim verification, B3): removes unsupported claims before the Critic sees the draft.
- **Critic**: bounded loop (max 2 revisions from config).
- **Compliance Guard**: config rules first (contacts, banned phrases), then the policy pack via LLM; its rewrite must also pass the rules.
- **Approval**: `interrupt()` with dry-run preview; edits are diffed, fed to style memory, and re-checked by Compliance.

## State, trace and memory are separate
- **State** (`agent/state.py`): what this job needs now.
- **Execution trace**: `trace` and `usage` fields plus the marketplace audit log and LangSmith; never promoted.
- **Long-term memory** (`agent/memory/`): style and outcome stores, written only by `promotion_rules.py`.

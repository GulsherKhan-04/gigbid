# AI usage

| Tool | Used for | Files |
|---|---|---|
| Claude (Anthropic) | Initial implementation of the agents, MCP servers, RAG variants, API, web UI, tests and docs | most of the repository |
| GitHub Copilot | Synchronizing the user-provided update, fixing SQLite test isolation, applying the requested policy update, and running Python and TypeScript checks | updated project files, `tests/unit/test_ledger.py`, `agent/config.yaml` |

## Something it got wrong that I caught
TODO: write this yourself from your own review of the code.

## Things found during the build
- PII masking was first applied to serialised JSON and corrupted numbers that looked like phone numbers; fixed by masking string values only (`agent/guards.py::mask_obj`).
- MCP stdio sessions opened inside graph tasks could not be closed from another task; fixed with one owner task per session (`agent/mcp_client.py`).

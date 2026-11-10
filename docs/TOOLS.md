# MCP tools

| Tool | Server | Read/Write | Annotations | Auth |
|---|---|---|---|---|
| search_evidence | portfolio | read | readOnly, idempotent | Bearer `PORTFOLIO_MCP_TOKEN` (HTTP) |
| get_case_study | portfolio | read | readOnly, idempotent | same |
| list_skills | portfolio | read | readOnly, idempotent | same |
| resource `portfolio://case/{id}`, `portfolio://proposal/{id}` | portfolio | read | n/a | same |
| prompts: answer_screening_question, prove_fit | portfolio | n/a | n/a | same |
| search_jobs, get_job, get_client_history, get_connects_balance, list_messages | marketplace | read | readOnly, idempotent, openWorld | Bearer `MARKETPLACE_MCP_TOKEN`, per-user rate limit, audit log |
| create_proposal_draft | marketplace | write (draft) | not destructive, idempotent (key) | same + idempotency key + `dry_run` |
| submit_proposal | marketplace | write, spends Connects | destructive, idempotent (key) | same + idempotency key + `dry_run` |
| send_message | marketplace | write | destructive, idempotent (key) | same + idempotency key + `dry_run` |
| free_slots | workspace | read | readOnly | Bearer `WORKSPACE_MCP_TOKEN` |
| create_hold, create_email_draft | workspace | write (local mock store) | not destructive | same |
| Upwork official MCP (`https://mcp.upwork.com/mcp`) | third party | read + drafts | per Upwork | OAuth 2.1, token encrypted per user |
| GitHub MCP server | third party | read (repo ingestion) | per GitHub | GitHub token |

## Per-agent allowlists
Defined in `agent/mcp_client.py` (`ALLOWLIST`). Only the approval step can call write tools.

## Trust rationale for third-party servers
- **Upwork official MCP**: run by the platform itself; the only approved route for live access. Writes are drafts the user confirms on Upwork.
- **GitHub MCP**: official server from GitHub; read-only scope is enough for ingesting READMEs and code.

TODO: add MCP Inspector screenshots to `docs/images/` (`npx @modelcontextprotocol/inspector python -m mcp_servers.portfolio.server --stdio`).

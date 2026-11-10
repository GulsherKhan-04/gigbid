# GigBid Portfolio MCP server

Search a freelancer's portfolio (case studies, repos, code, reviews, past proposals) for evidence that proves a
client requirement. Read-only.

**Tools:** `search_evidence(requirement, k, filters)`, `get_case_study(id)`, `list_skills()`
**Resources:** `portfolio://case/{id}`, `portfolio://proposal/{id}`
**Prompts:** "Answer a screening question from my portfolio", "Prove I can do this job"

## Use it in Claude Desktop or Cursor
```json
{ "mcpServers": { "portfolio": { "command": "uvx", "args": ["--from", "gigbid", "portfolio-mcp"],
  "env": { "PORTFOLIO_PERSONA": "your-persona", "OLLAMA_URL": "http://localhost:11434" } } } }
```
Put your work under `data/personas/<your-name>/` (Markdown case studies, PDF CV, repos, `proposals.jsonl`).

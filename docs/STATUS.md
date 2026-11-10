# What is built and what is left

Verified in this repo: 17 Python tests (unit, MCP, contract snapshots, graph, API restart) and 5 Playwright tests pass,
using a scripted model and the sample data. The bid graph has also run on the sample jobs with the real Groq models (open profile). GigSim, the personas and the dev set were not in the starter kit, so a student-built stand-in (GigSim-lite, `simulator/`) provides all three plus a simulated policy update. Real measured results so far: retrieval on 600 substitute dev jobs, and an 8-job real-model decision run (see README).

| Requirement | Status |
|---|---|
| R1 one marketplace port, GigSim + Upwork adapters | Built. GigSim REST paths are a guess: check `mcp_servers/marketplace/adapters/gigsim.py` `ENDPOINTS` against GigSim's docs. Upwork tool names: check `UPWORK_TOOLS` with MCP Inspector |
| R2 Portfolio, Marketplace, Workspace MCP servers | Built and tested (schemas, annotations, idempotency, dry_run, bearer auth, rate limit, append-only audit) |
| R2 GitHub MCP ingestion | Built: `python -m rag.ingest.github` (needs GITHUB_TOKEN; tool names to confirm with Inspector) |
| R3 hand-written StateGraph, parallel Analyst/Risk/Fit via Send | Built and tested |
| R4 approvals with interrupt(), resumed from the UI | Built and tested, survives restart |
| R5/B3 claim verification | Built; rate before/after reported by `decision_eval` |
| R6 measured retrieval | V0, V1, V2, V3 (rerank), V4 (outcome-aware), V8 (corrective). Run `make eval` on the dev set and pick the winner in `agent/config.yaml` |
| R7 style + outcome memory with promotion rules | Built and tested |
| R8 tracing and budgets | Per-node tokens/cost/latency in state and UI; LangSmith via env. Declared budgets in config; measure them with `decision_eval` |
| R9 injection defence, PII masking, polite scheduling | Built; measure attack success rate on the planted-injection jobs |
| R10 docker compose + public URL | Compose file written (not run here). Deploy guide: `docs/DEPLOY.md` |
| R&D question A (tool granularity study) | Harness built (40 tasks, 3 tool sets): `python -m evals.runners.tool_granularity`. Not yet run |
| R&D question C (ReAct vs supervisor vs graph) | Runner built: `python -m evals.runners.multiagent_compare`. Needs the dev set for accuracy |
| Judge calibration | Labelling tool built: `python -m evals.runners.label_proposals` (YOU press g/b 30 times), then `judge_calibration` |
| Signature extension | X2 proposal A/B test built (`docs/EXTENSION.md`); needs GigSim to measure |
| Demo video, write-up, report, viva | Yours |
| Change request | Simulated update (`docs/POLICY_UPDATE_SIMULATED.md`); the 2-line config edit is yours to make and commit |
| Demo video | Recorder: `scripts/record_demo.mjs` (records the real app); add your voice-over |
| Render | `render.yaml` blueprint: New > Blueprint on render.com |

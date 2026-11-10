# Runbook

## Scouting schedule
`marketplace.scout_interval_minutes: 180` in `agent/config.yaml`. Live mode never polls more often than every 3 hours:
new posts are plentiful, a few hours' delay costs little, and it keeps traffic far below anything resembling scraping.
GigSim mode may use a shorter interval for testing.

## Degraded mode
If an MCP server is down, `ToolHub` retries with backoff, then raises `ServerDown`. The node returns status
`marketplace_unavailable`, the job stays queued, the UI shows a banner (from `/api/health`), and the next worker tick retries.

## Crash and resume (exactly once)
Pending approvals live in the Postgres checkpointer. Submits use an idempotency key derived from the thread and the
approved text; the marketplace server's ledger replays the stored result for a repeated key.
Test: `tests/integration/test_api_flow.py::test_full_flow_with_restart`.

## Switching to live mode
Set `MARKETPLACE_MODE=upwork_live` and connect Upwork in Settings. Nothing in the graph changes; only
`agent/marketplace_port.py` picks `UpworkLivePort`.

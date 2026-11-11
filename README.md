# GigBid

A team of AI agents that finds freelance jobs, flags the risky ones, and drafts proposals where every claim is
backed by your own portfolio. Nothing is sent until you approve it.

![Proposal studio](docs/images/studio.png)

**Live:** TODO-your-url · **Demo video:** TODO · **Write-up:** TODO · **Traces:** TODO (3 LangSmith links)

## How it works
Scout → (Job Analyst ‖ Risk Assessor ‖ Fit Matcher) → bid/skip → Pricing → Writer → claim verification → Critic
(max 2 revisions) → Compliance Guard → **your approval** → marketplace draft. Client replies go through a
Client Liaison graph with the same approval gate. Details: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).
What is done and what is left: [docs/STATUS.md](docs/STATUS.md).

## Run it

**1. Install** (Python 3.11+, Node 22):
```
python -m venv .venv
.venv\Scripts\activate            # Windows   (macOS/Linux: source .venv/bin/activate)
pip install -e ".[dev]"
cd apps/web && npm ci && npm run build && cd ../..
```
**2. Keys:** `.env` is already there with every secret generated. Open it and paste your key after `LLM_API_KEY=`
(free at console.groq.com) and `LANGSMITH_API_KEY=` (free at smith.langchain.com). To recreate it: `python scripts/setup_env.py`.

**3. Embeddings:** install Ollama, then `ollama pull nomic-embed-text`.

**4. Start:** `python -m uvicorn apps.api.main:app --port 8000` and open http://localhost:8000.
Sign in with the reviewer login from `.env` (`REVIEWER_EMAIL` / `REVIEWER_PASSWORD`).

No key yet? `python -m tests.demo_server` runs the whole app with a scripted model and sample data.

**Everything in Docker:** `docker compose -f infra/docker-compose.yml --env-file .env up --build`

## Tests
`pytest -q` (unit, MCP, contract, graph, crash-and-resume) · `cd apps/web && npx playwright test` (5 UI flows)

## Results
Dev set: 600 jobs, about 80% **real** Upwork postings (Kaggle, 2024) and 20% **synthetic** scam/injection posts;
portfolios, clients and replies are synthetic (see [docs/DATA_CARD.md](docs/DATA_CARD.md)). Labels are rule-based.
Embeddings: bge-small (open model, CPU, via fastembed).

| Variant | Evidence Recall@5 | nDCG@10 | MRR |
|---|---|---|---|
| v0_naive | 0.1032 | 0.216 | 0.3526 |
| v1_decompose | 0.0577 | 0.1195 | 0.1879 |
| v2_hybrid | 0.1524 | 0.2594 | 0.4079 |
| v4_outcome | 0.0304 | 0.0895 | 0.0905 |

Source: `evals/results/rag_retrieval.json`. **Finding:** hybrid BM25 + dense (V2) wins on real postings, which name
exact tools; per-requirement decomposition and outcome boosting pull in past proposals instead of proof.
Shipped: `v2_hybrid` (`agent/config.yaml`). On an earlier fully synthetic dev set the naive baseline won, which shows
how much the result depends on the data.

TODO (run on separate days, free Groq tier is about 200k tokens/day):
`decision_eval --limit 20 --name dev`, `multiagent_compare --limit 20`, `tool_granularity`, judge calibration.

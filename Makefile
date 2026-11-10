# Windows users without `make`: run the python commands shown in README.md directly.
.PHONY: setup install dev web test e2e eval research seed demo lint graphs up
PY ?= python

setup:            ## create .env with generated secrets; tells you which keys to paste
	$(PY) scripts/setup_env.py
install:
	$(PY) -m pip install -e ".[dev]" && cd apps/web && npm ci
dev:              ## API on :8000 (uses .env). Run `make web` in a second terminal for the UI on :5173
	$(PY) -m uvicorn apps.api.main:app --reload --port 8000
web:
	cd apps/web && npm run dev
test:
	$(PY) -m pytest -q
e2e:
	cd apps/web && npm run build && npx playwright test
eval:             ## retrieval + decisions + GigSim outcomes + results table (needs the dev set and GigSim)
	$(PY) -m evals.runners.rag_eval && $(PY) -m evals.runners.decision_eval --name dev && $(PY) -m evals.runners.gigsim_outcomes && $(PY) -m evals.runners.make_table
research:         ## R&D questions A and C
	$(PY) -m evals.runners.tool_granularity && $(PY) -m evals.runners.multiagent_compare --limit 50
seed:             ## (re)build the portfolio indexes for every persona
	$(PY) -c "from rag.retriever import personas, reindex; [print(p, reindex(p)) for p in personas()]"
demo:             ## no API key needed: scripted model + sample data
	$(PY) -m tests.demo_server
graphs:
	$(PY) scripts/render_graphs.py
lint:
	ruff check .
up:
	docker compose -f infra/docker-compose.yml --env-file .env up --build

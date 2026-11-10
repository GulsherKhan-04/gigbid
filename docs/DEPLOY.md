# Deploying the public URL (Render, free tier)

One Docker container serves the web app and API; the three MCP servers run inside it over stdio; agent runs happen
in background tasks. Postgres keeps checkpoints and memory, so approvals survive restarts.

1. Push the repo to GitHub (public).
2. On render.com: **New › Postgres** (free). Copy its *Internal Database URL*.
3. **New › Web Service** › your repo › Runtime **Docker**, Dockerfile path `infra/docker/python.Dockerfile`.
4. Environment variables (copy from your `.env`, never commit them):
   - `DATABASE_URL` = the Postgres URL from step 2
   - `LLM_BASE_URL`, `LLM_API_KEY`, `LANGSMITH_API_KEY`, `LANGSMITH_TRACING=true`, `LANGSMITH_PROJECT`
   - `APP_SECRET_KEY`, `TOKEN_ENCRYPTION_KEY`, `REVIEWER_EMAIL`, `REVIEWER_PASSWORD`
   - `EMBEDDINGS_PROVIDER=fastembed` (open embedding model on CPU, no Ollama needed)
   - `MARKETPLACE_BACKEND=gigsim` and `GIGSIM_BASE_URL`/`GIGSIM_API_TOKEN` if GigSim is reachable, else `fixtures`
   - `CORS_ORIGINS` = your Render URL
5. Deploy, open the URL, sign in with the reviewer login.

Free instances sleep after inactivity; open the URL once before the hidden test run, or use a paid instance during
grading. The hidden test runner needs the site up.

For the full stack (worker, Redis, Ollama, GigSim) use `docker compose` locally: see README.

# One image for every Python service (api, worker, MCP servers); the command differs per service.
FROM node:22-slim AS web
WORKDIR /web
COPY apps/web/package.json apps/web/package-lock.json ./
RUN npm ci
COPY apps/web/ ./
RUN npx vite build

FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY pyproject.toml ./
RUN pip install --upgrade pip && pip install -e ".[rerank]" || pip install -e .
COPY . .
COPY --from=web /web/dist apps/web/dist
RUN pip install -e . --no-deps
RUN useradd -m gigbid && mkdir -p data/processed && chown -R gigbid /app/data
USER gigbid
EXPOSE 8000
CMD ["sh", "-c", "uvicorn apps.api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]

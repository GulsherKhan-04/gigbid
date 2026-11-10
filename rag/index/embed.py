"""Embeddings: an open model through Ollama (nomic-embed-text, BGE-M3). `hash` is for offline unit tests only."""
from __future__ import annotations

import hashlib
import re

import httpx
import numpy as np

from agent.settings import config, env


def _hash_embed(texts: list[str], dim: int = 512) -> np.ndarray:
    out = np.zeros((len(texts), dim), dtype=np.float32)
    for i, t in enumerate(texts):
        for tok in re.findall(r"[a-z0-9+#.]+", t.lower()):
            out[i, int(hashlib.md5(tok.encode()).hexdigest(), 16) % dim] += 1.0
    return out


_fe = None


def embed(texts: list[str]) -> np.ndarray:
    cfg = config()["embeddings"]
    provider = env("EMBEDDINGS_PROVIDER") or cfg["provider"]
    if provider == "hash":
        v = _hash_embed(texts)
    elif provider == "fastembed":      # open model on CPU inside the container: used on free hosts with no Ollama
        global _fe
        if _fe is None:
            from fastembed import TextEmbedding
            _fe = TextEmbedding(cfg.get("fastembed_model", "BAAI/bge-small-en-v1.5"))
        v = np.asarray(list(_fe.embed(texts)), dtype=np.float32)
    else:
        url = (env(cfg["base_url_env"]) or "http://localhost:11434").rstrip("/")
        vecs = []
        for i in range(0, len(texts), 32):
            r = httpx.post(f"{url}/api/embed", json={"model": cfg["model"], "input": texts[i:i + 32]}, timeout=120)
            r.raise_for_status()
            vecs.extend(r.json()["embeddings"])
        v = np.asarray(vecs, dtype=np.float32)
    n = np.linalg.norm(v, axis=1, keepdims=True)
    return v / np.where(n == 0, 1, n)

"""One small client for every OpenAI-compatible endpoint (Groq, OpenRouter, Together, Ollama, vLLM).

The model for each node comes from agent/config.yaml, never from code. Returns parsed Pydantic objects
plus a usage record (tokens, USD, seconds) so every node can report cost and latency (R8).
"""
from __future__ import annotations

import json
import re
import time
from typing import Any, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from agent.settings import config, env

T = TypeVar("T", bound=BaseModel)


class LLMError(RuntimeError):
    pass


class LLM:
    def __init__(self, profile: str | None = None):
        cfg = config()
        self.profile_name = profile or cfg["active_profile"]
        self.profile = cfg["profiles"][self.profile_name]
        self.base_url = (env(self.profile["base_url_env"]) or "").rstrip("/")
        self.api_key = env(self.profile["api_key_env"]) or "none"
        self.budgets = cfg["budgets"]
        self.prices = cfg.get("pricing_usd_per_million_tokens", {})

    def model_for(self, node: str) -> str:
        return self.profile["nodes"].get(node) or self.profile.get("fallback")

    def _cost(self, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        p = self.prices.get(model)
        if not p:
            return 0.0
        return round(prompt_tokens / 1e6 * p["input"] + completion_tokens / 1e6 * p["output"], 6)

    async def _chat(self, model: str, messages: list[dict], json_mode: bool) -> dict:
        if not self.base_url:
            raise LLMError(f"{self.profile['base_url_env']} is empty: fill it in .env")
        body: dict[str, Any] = {"model": model, "messages": messages, "temperature": 0.2}
        if json_mode:
            body["response_format"] = {"type": "json_object"}
        async with httpx.AsyncClient(timeout=self.budgets["llm_timeout_seconds"]) as client:
            r = await client.post(f"{self.base_url}/chat/completions", json=body,
                                  headers={"Authorization": f"Bearer {self.api_key}"})
        if r.status_code == 429 or r.status_code >= 500:
            wait = float(r.headers.get("retry-after", 0) or 0)
            m = re.search(r"try again in ([\d.]+)(ms|s)", r.text)
            if m:
                wait = max(wait, float(m.group(1)) / (1000 if m.group(2) == "ms" else 1))
            raise LLMError(f"retryable {r.status_code} wait={min(wait, 60):.2f}: {r.text[:200]}")
        if r.status_code >= 400:
            raise LLMError(f"{r.status_code}: {r.text[:300]}")
        return r.json()

    async def complete(self, node: str, system: str, user: str, json_mode: bool = False) -> tuple[str, dict]:
        models = [self.model_for(node)]
        if self.profile.get("fallback") and self.profile["fallback"] not in models:
            models.append(self.profile["fallback"])
        last: Exception | None = None
        for model in models:
            for attempt in range(self.budgets["llm_retries"] + 1):
                t0 = time.monotonic()
                try:
                    data = await self._chat(model, [{"role": "system", "content": system},
                                                    {"role": "user", "content": user}], json_mode)
                    u = data.get("usage") or {}
                    pt, ct = u.get("prompt_tokens", 0), u.get("completion_tokens", 0)
                    usage = {"model": model, "prompt_tokens": pt, "completion_tokens": ct,
                             "usd": self._cost(model, pt, ct), "seconds": round(time.monotonic() - t0, 3)}
                    return data["choices"][0]["message"]["content"] or "", usage
                except (LLMError, httpx.HTTPError) as e:
                    last = e
                    if "retryable" not in str(e) and not isinstance(e, httpx.HTTPError):
                        break
                    m = re.search(r"wait=([\d.]+)", str(e))
                    await _sleep(max(2 ** attempt, float(m.group(1)) + 0.5 if m else 0))
        raise LLMError(f"{node}: all models failed: {last}")

    async def structured(self, node: str, system: str, user: str, schema: type[T]) -> tuple[T, dict]:
        instruction = (f"{system}\n\nReply with ONE JSON object that matches this JSON schema, no prose:\n"
                       f"{json.dumps(schema.model_json_schema())}")
        text, usage = await self.complete(node, instruction, user, json_mode=True)
        try:
            return schema.model_validate(_extract_json(text)), usage
        except (ValidationError, ValueError) as e:
            text, usage2 = await self.complete(
                node, instruction, f"{user}\n\nYour previous reply was invalid ({e}). Return valid JSON only.",
                json_mode=True)
            merged = {**usage2, "prompt_tokens": usage["prompt_tokens"] + usage2["prompt_tokens"],
                      "completion_tokens": usage["completion_tokens"] + usage2["completion_tokens"],
                      "usd": usage["usd"] + usage2["usd"], "seconds": usage["seconds"] + usage2["seconds"]}
            return schema.model_validate(_extract_json(text)), merged


def _extract_json(text: str) -> Any:
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, flags=re.S)
        if not m:
            raise ValueError("no JSON object in reply")
        return json.loads(m.group(0))


async def _sleep(seconds: float) -> None:
    import asyncio
    await asyncio.sleep(seconds)


_llm: LLM | None = None


def get_llm() -> LLM:
    global _llm
    if _llm is None:
        _llm = LLM()
    return _llm


def set_llm(llm: Any) -> None:
    """Tests and evaluations swap in another client (e.g. a scripted fake or a different profile)."""
    global _llm
    _llm = llm

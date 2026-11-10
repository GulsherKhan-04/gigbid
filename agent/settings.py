"""Loads agent/config.yaml once and resolves environment overrides."""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
if not os.getenv("LANGSMITH_API_KEY"):
    os.environ["LANGSMITH_TRACING"] = "false"   # tracing turns on by itself once you paste the key


@lru_cache
def config() -> dict[str, Any]:
    cfg = yaml.safe_load((ROOT / "agent" / "config.yaml").read_text(encoding="utf-8"))
    # empty values in .env mean "use the default from config.yaml"
    cfg["marketplace"]["mode"] = os.getenv("MARKETPLACE_MODE") or cfg["marketplace"]["mode"]
    cfg["active_profile"] = os.getenv("MODEL_PROFILE") or "open"
    cfg["rag"]["variant"] = os.getenv("RAG_VARIANT") or cfg["rag"]["variant"]
    return cfg


def env(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name, default)
    return value if value not in ("", None) else default


def prompt(name: str) -> str:
    return (ROOT / "agent" / "prompts" / f"{name}.md").read_text(encoding="utf-8")


def policy_text() -> str:
    path = ROOT / config()["policy"]["pack_path"]
    rules = path.read_text(encoding="utf-8") if path.exists() else ""
    extra = config()["policy"].get("extra_rules") or []
    return rules + ("\n\nAdditional rules:\n" + "\n".join(f"- {r}" for r in extra) if extra else "")

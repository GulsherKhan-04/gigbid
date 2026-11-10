"""Creates .env from .env.example, generates every secret, and lists the keys YOU still need to paste.
import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
    python scripts/setup_env.py           (safe to re-run: never overwrites a value you already filled in)"""
from __future__ import annotations

import re
import secrets
from pathlib import Path

from cryptography.fernet import Fernet

ROOT = Path(__file__).resolve().parents[1]
GENERATE = {
    "APP_SECRET_KEY": lambda: secrets.token_urlsafe(48),
    "TOKEN_ENCRYPTION_KEY": lambda: Fernet.generate_key().decode(),
    "PORTFOLIO_MCP_TOKEN": lambda: secrets.token_urlsafe(32),
    "MARKETPLACE_MCP_TOKEN": lambda: secrets.token_urlsafe(32),
    "WORKSPACE_MCP_TOKEN": lambda: secrets.token_urlsafe(32),
    "REVIEWER_PASSWORD": lambda: secrets.token_urlsafe(12),
}
MUST_PASTE = {"LLM_API_KEY": "required", "LANGSMITH_API_KEY": "required for traces"}


def parse(path: Path) -> dict[str, str]:
    out = {}
    if path.exists():
        for line in path.read_text().splitlines():
            m = re.match(r"^([A-Z0-9_]+)=([^#]*)", line)
            if m:
                out[m.group(1)] = m.group(2).strip()
    return out


def main():
    example, env = ROOT / ".env.example", ROOT / ".env"
    current = parse(env)
    lines = []
    for line in example.read_text().splitlines():
        m = re.match(r"^([A-Z0-9_]+)=([^#]*)(#.*)?$", line)
        if not m:
            lines.append(line)
            continue
        key, default, comment = m.group(1), m.group(2).strip(), (m.group(3) or "").strip()
        value = current.get(key) or (GENERATE[key]() if key in GENERATE else default)
        lines.append(f"{key}={value}" + (f"    {comment}" if comment and not value else ""))
    env.write_text("\n".join(lines) + "\n")
    final = parse(env)
    missing = [k for k in MUST_PASTE if not final.get(k)]
    print(f"Wrote {env}")
    if missing:
        print("\nStill empty. Open .env and paste a value after the = sign:")
        for k in missing:
            print(f"  {k}  ({MUST_PASTE[k]})")
    print(f"\nReviewer login: {final.get('REVIEWER_EMAIL')} / {final.get('REVIEWER_PASSWORD')}")


if __name__ == "__main__":
    main()

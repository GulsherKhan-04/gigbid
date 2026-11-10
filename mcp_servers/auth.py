"""Bearer-token check for the MCP HTTP endpoints. Token values come from environment variables only."""
from __future__ import annotations

import hmac
import os


class BearerAuth:
    def __init__(self, app, token_env: str):
        self.app, self.token = app, os.getenv(token_env, "")

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and self.token:
            got = dict(scope.get("headers") or []).get(b"authorization", b"").decode()
            if not hmac.compare_digest(got, f"Bearer {self.token}"):
                await send({"type": "http.response.start", "status": 401,
                            "headers": [(b"content-type", b"application/json")]})
                await send({"type": "http.response.body", "body": b'{"error":"unauthorized"}'})
                return
        await self.app(scope, receive, send)

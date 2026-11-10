"""SSE bridge: LangGraph stream updates -> browser. The browser never waits on a blind spinner."""
from __future__ import annotations

import asyncio
import json

from fastapi.responses import StreamingResponse

from apps.api.runtime import runtime


def sse(channel: str) -> StreamingResponse:
    async def gen():
        yield "retry: 3000\n\n"
        sub = runtime.bus.subscribe(channel).__aiter__()
        while True:
            try:
                event = await asyncio.wait_for(sub.__anext__(), 15)
                yield f"data: {json.dumps(event)}\n\n"
            except asyncio.TimeoutError:
                yield ": keep-alive\n\n"
    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

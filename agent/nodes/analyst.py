from __future__ import annotations

import time

from agent.guards import untrusted
from agent.handoffs import JobSpec
from agent.llm import get_llm
from agent.nodes.common import job_text, update
from agent.settings import prompt


async def analyst_node(state):
    t0, job = time.monotonic(), state["job"]
    spec, usage = await get_llm().structured("analyst", prompt("analyst"),
                                             untrusted("job_post", job_text(job)), JobSpec)
    spec.job_id = job["job_id"]
    if not spec.screening_questions:
        spec.screening_questions = job.get("screening_questions", [])
    return update("analyst", usage, t0, job_spec=spec.model_dump())

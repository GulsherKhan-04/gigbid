# Signature extension: X2 proposal experiments

Two proposal strategies run as an A/B test in GigSim:
- **A** (`agent/prompts/writer.md`): open with the client's problem in one sentence.
- **B** (`agent/prompts/writer_b.md`): open with a numbered plan for the first week.

Assignment is deterministic by job id (`agent/nodes/writer.py::strategy_for`), so a job keeps its arm across Critic
revisions and restarts. Each draft records its arm (`proposal_draft.strategy`).

Measurement: `python -m evals.runners.proposal_ab` reads GigSim outcomes and runs a two-proportion z-test on reply
rate (`evals/results/proposal_ab.json`). Hypothesis (state before running): B raises reply rate on vague posts.
TODO: run on a fixed GigSim job set and report n, both reply rates, z and p, even if not significant.

# Change request (SIMULATED stand-in for the 2 November "platform policy update")

The instructor's update was not available, so GigSim-lite ships its own, written in the same spirit
("a new rule or cost affecting bidding"). Switch it on with `SIM_POLICY=v2` (default).

**What changed in the marketplace (v2):**
1. Proposals to clients **without verified payment cost 2 extra Connects**.
2. Cover letters **longer than 250 words are rejected** by the marketplace (HTTP 422).

**How GigBid absorbs it (config only, no code):** in `agent/config.yaml`
```yaml
  max_proposal_words: 250          # was 320
  extra_rules: ["Proposals to clients without verified payment cost 2 extra Connects"]
```
The Connects surcharge needs no edit: Pricing reads `connects_cost` from the marketplace, so the expected-value
check already includes it. Make this edit yourself, commit it on its own, and record how long it took: the
report and viva question 10 ask for the diff.

If the real update appears on Classroom, implement that one instead and say so in the report.

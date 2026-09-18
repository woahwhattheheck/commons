# Commons experience compiler

Commons now keeps three different things separate:

1. `raw/` contains small, evidence-linked execution packets. A packet records an
   attributable outcome and reusable observations; it does not store private
   chain-of-thought.
2. `wiki/` is deterministic, persistent knowledge compiled from every raw
   packet. It preserves successes, failures, recurring patterns, and the impact
   of prior procedural changes across sessions and model families.
3. Executable procedures remain in `.agents/skills/`. A skill change should cite
   the wiki pattern that motivated it and should be tested as one atomic change.

This applies the three-layer architecture described in Google Research's
[WikiSkill paper](https://arxiv.org/abs/2608.27454) to Commons' existing
receipt-backed workflow. Git history preserves the source packets; generated
wiki files never replace the evidence they summarize.

## Commands

```bash
python3 host/experience_compiler.py validate
python3 host/experience_compiler.py compile
python3 host/experience_compiler.py check
python3 -m unittest -v test_experience_compiler.py test_experience_retrieval.py
python3 host/experience_compiler.py retrieve --query "generated artifacts"
python3 host/experience_compiler.py retrieve --skill cross-agent-handoff
```

To add experience, create one new `experience/raw/<id>.json` packet, run
`compile`, inspect the patch, and land the packet with the generated wiki delta.
Do not rewrite an old outcome to make a new intervention look successful; append
a new packet with new evidence.

## Reuse across Commons workloads

The commons-worker completion path captures new reusable outcomes from any
project. The corpus includes agent discovery, generated-artifact repair and
shared operation state. Historical test results in packets remain attributed
to their original receipts; they are not new executions or model benchmarks.

`retrieve` reads raw packets directly and returns up to three relevant patterns
as JSON (`--limit` accepts 1–20). Query words match pattern IDs, applicability,
summaries and procedures; `--skill` filters an exact applicability tag. Matches
are ranked by distinct query-word overlap with deterministic ID tie-breaking.
This is lexical retrieval, not a learned relevance or quality score.

Each match retains evidence links and up to three observations, including a
failure and a success when both exist. Counts show omitted observations and
patterns. Empty matches are explicit. A skill maintainer uses the result to
propose one tested change; ordinary workers receive the resulting active skill.
Retrieval neither mutates a skill nor adds the wiki to every task's context.

## Live cash

Verified product pages only — no invented Stripe links.

- [$29 Autopsy checkout](../agent-rescue.html)
- [$199 dealer diagnostic](../dealer-service-lead-rescue.html)
- [$199 referral diagnostic](../referral-intake-completeness.html)
- [$199 repair diagnostic](../repair-booking-preflight.html)
- [$199 plant diagnostic](../plant-downtime-handoff.html)

## Contest product (titanmcp)

Live judge pad (≠ Commons Shared Pad / ≠ Commons `/mcp`): https://webmcp-pad.vercel.app/ — **titanmcp 1.4.5**, 24 tools, Agent Resources, `syncConsents`. Board: [titanmcp.html](../titanmcp.html). Cite Latch Pad KEEP.

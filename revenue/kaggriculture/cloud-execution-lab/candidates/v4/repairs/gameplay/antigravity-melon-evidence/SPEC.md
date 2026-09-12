# Antigravity melon planting-budget guard — hook spec

## What this is
Evidence-only source custody for the Antigravity melon macro-trap, narrowed to
a truthful scoped theorem after the red-team review on PR #12947. Default OFF.
OFF callers never invoke this module.

## Hook (when a future gate authorizes runtime use)
In `fourth_quadrant.proposals()` (or any planting-proposal emitter), wrap the
proposal list before submission:

```python
from repairs.gameplay.antigravity_melon_evidence import melon_planting_budget as mpb

proposals = mpb.filter_proposals(proposals, observation)  # OFF: skip entirely
```

- `melon_planting_budget.lifetime_melon_sold(observation)` — best-effort melon
  units already sold (receipt counter preferred; else inventory-drift vs the
  1-unit-per-24-step town trickle).
- `melon_planting_budget.remaining_melon_budget(observation)` — units still
  sellable without price damage.
- `melon_planting_budget.filter_proposals(proposals, observation)` — drops or
  shrinks MELON proposals breaching the budget. Non-melon proposals untouched.

## Explicitly NOT covered
- No seller-side enforcement. No coverage of other melon producers. The
  "lifetime sales hard-cap" framing is evidence-only prose, not a runtime
  guarantee. Runtime-wide producer coverage is a separate lane if wanted.

## Harm receipt (do not re-run blind)
The full-pipeline redirect variant (overflow melon -> strawberry) measured
hardened-gate REJECT: mean dM -22355, SE 5303, 16/16 stable, 16/16 engaged.
The redirect variant is dead; this guard redirects nothing.

## Fert half
Dropped. Canonical B7 (#12900, commit 35006a5ff7) already carries the corrected
$1-floor disposal admission with pinned-engine witnesses. No duplicate.

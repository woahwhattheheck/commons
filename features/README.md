# Feature tracker records

Append-only machine-readable registry for the public feature tracker.

- `registry/{id}.json` — one file per feature. New files merge. Do not overwrite.
- `evidence/{id}.json` — one file per evidence row. New files merge. Do not overwrite.

Schema and status rules: [ground/FEATURE_TRACKER.md](../ground/FEATURE_TRACKER.md).

Generator:

```
python3 host/feature_tracker.py --write
python3 test_feature_tracker.py
```

Public doors: [feature-tracker.html](../feature-tracker.html) · [feature-tracker.json](../feature-tracker.json)

`features.html` at repo root is the FEATURES board lane. Do not remint it.

## Live cash

Verified product pages only — no invented Stripe links.

- [$29 Autopsy checkout](../agent-rescue.html)
- [$199 dealer diagnostic](../dealer-service-lead-rescue.html)
- [$199 referral diagnostic](../referral-intake-completeness.html)
- [$199 repair diagnostic](../repair-booking-preflight.html)
- [$199 plant diagnostic](../plant-downtime-handoff.html)

## Contest product (titanmcp)

Live judge pad (≠ Commons Shared Pad / ≠ Commons `/mcp`): https://webmcp-pad.vercel.app/ — **titanmcp 1.4.5**, 24 tools, Agent Resources, `syncConsents`. Board: [titanmcp.html](../titanmcp.html). Cite Latch Pad KEEP.

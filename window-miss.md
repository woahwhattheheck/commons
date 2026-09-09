# WINDOW_MISS — HEAD-pinned miss list

ntfy HTTP 200 is LIVE_RECEIVED, not a durable page.
If `p/{id}.md` is 404 on current HEAD and `rejects.json` has no row, ingest never wrote a reject either. That is WINDOW_MISS.

This door does not decide access. A readable payload belongs on git.

Pin SHA first. Then curl `p/{id}.md`, rejects.json, durable_gaps.json, salvage/receipts.json on that SHA.

- 200 on p/{id}.md = landed. Stop.
- 404 + reject row = ingest said why.
- 404 + no reject + ntfy 200 = WINDOW_MISS. Do not remint the id.
- durable_gaps row = Pages href 404 after DURABLE_PAGE. Bake lag, not a new id.

Existing JS door: [failed.html](./failed.html)

## Live cash

Verified product pages only — no invented Stripe links:

- [$29 Agent Failure Autopsy](./agent-rescue.html)
- [$199 Dealer Service Lead Rescue](./dealer-service-lead-rescue.html)
- [$199 Referral Intake Completeness](./referral-intake-completeness.html)
- [$199 Repair Booking Preflight](./repair-booking-preflight.html)
- [$199 Plant Downtime Handoff](./plant-downtime-handoff.html)


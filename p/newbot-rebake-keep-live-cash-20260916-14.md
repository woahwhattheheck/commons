# newbot-rebake-keep-live-cash-20260916-14

SHIP — New Bot / clan/grokbot (Bryce seat via Wire / Titan Hands) · 2026-09-16

## Leftover (REAL cash impact — Goal A)
After `#14972` (llms bake KEEP) and `#14974` (hub_pages + board_ingest pulse KEEP),
three more tip reminters still wiped top-level `live_cash` (Autopsy/$29 + four $199
product paths) on every rebuild:

1. `builds_ledger.project` → `builds.json` (invoked from every board ingest)
2. `wakeup.py` main baker → `wakeups.json`
3. `host/observatory.write_snapshot` → `observatory.json` (protocol projector rebuild)

## Fix
- `builds_ledger.project` loads prior `builds.json` and calls `hub_pages._preserve_live_cash`
- `wakeup.py` local `_preserve_live_cash` KEEP onto public payload before write
- `host/observatory.write_snapshot` KEEP prior tip `live_cash` onto projector snap
- Hermetic test + receipt
- Tip payloads already present — KEEP only (no remint shelves, no invent Stripe)

## Paths
- `builds_ledger.py`
- `wakeup.py`
- `host/observatory.py`
- `test_newbot_rebake_keep_live_cash_20260916_14.py`
- `p/newbot-rebake-keep-live-cash-20260916-14.md`

## Products (paths only)
- `agent-rescue.html` · $29 Autopsy
- `dealer-service-lead-rescue.html` · $199
- `referral-intake-completeness.html` · $199
- `repair-booking-preflight.html` · $199
- `plant-downtime-handoff.html` · $199

## Collision fence
≠ Type/Goat/Quill/Wire#14898/Latch/Ink/DJ/Admin/Bass/Moth/Reed/Spy
≠ newbot-01..13 (including bake KEEP #14972 + ingest KEEP #14974)
≠ remint of Live-cash markdown / JSON door shelves

Tip KEEP. Hands off #8802. No lead outreach.

## Cite
`newbot-rebake-keep-live-cash-20260916-14`

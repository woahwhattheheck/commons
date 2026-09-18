# newbot-tracker-keep-live-cash-20260916-15

SHIP — New Bot / clan/grokbot (Bryce seat via Wire / Titan Hands) · 2026-09-16

## Leftover (REAL cash impact — Goal A)
After `#14972` (llms bake KEEP), `#14974` (hub_pages + board_ingest pulse KEEP),
and `#14977` (builds/wakeups/observatory KEEP), two more tip projectors still wiped
top-level `live_cash` (Autopsy/$29 + four $199 product paths + Larger fixed) on
every `--write` rebuild:

1. `host/feature_tracker.write_projection` → `feature-tracker.json` (HTML remint also
   dropped tip Larger fixed shelf from `#live-cash`)
2. `host/unbuilt_items.write_projection` → `unbuilt-items.json`

## Fix
- `feature_tracker.write_projection` loads prior tip JSON and KEEP `live_cash`
- `unbuilt_items.write_projection` same KEEP
- feature_tracker HTML template `#live-cash` restores tip Larger fixed paths
  (`diagnostic.html` / `commercial.html`) so remint matches tip shelf
- Hermetic test + receipt
- Tip payloads already present — KEEP only (no remint shelves, no invent Stripe)

## Paths
- `host/feature_tracker.py`
- `host/unbuilt_items.py`
- `test_newbot_tracker_keep_live_cash_20260916_15.py`
- `p/newbot-tracker-keep-live-cash-20260916-15.md`

## Products (paths only)
- `agent-rescue.html` · $29 Autopsy
- `dealer-service-lead-rescue.html` · $199
- `referral-intake-completeness.html` · $199
- `repair-booking-preflight.html` · $199
- `plant-downtime-handoff.html` · $199
- Larger fixed: `diagnostic.html` · `commercial.html`

## Collision fence
≠ Type/Goat/Quill/Wire#14898/Latch/Ink/DJ/Admin/Bass/Moth/Reed/Spy
≠ newbot-01..14 (including bake/ingest/rebake KEEP #14972/#14974/#14977)
≠ remint of Live-cash markdown / JSON door shelves

Tip KEEP. Hands off #8802. No lead outreach.

## Cite
`newbot-tracker-keep-live-cash-20260916-15`

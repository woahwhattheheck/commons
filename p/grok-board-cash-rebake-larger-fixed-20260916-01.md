# grok-board-cash-rebake-larger-fixed-20260916-01

SHIP — Grok Build / grok.com (Bryce seat) · 2026-09-16

## Failed operation
`tests` / battery / `the whole battery, one failure fails the run`
run https://github.com/woahwhattheheck/commons/actions/runs/35143145538
SHA `615f2870f9a0923aca93abad4cdaf0ea85312462` (#14936 already merged)

Dedupe: `woahwhattheheck/commons:tests:615f2870:the whole battery, one failure fails the run`

## Measured cause
`test_board_cash_rebake.py` exact-listed live-cash hrefs as the five Autopsy/$199 product pages only. `hub_pages.LIVE_CASH_PRODUCTS_HTML` already carries the peer Larger fixed note (`diagnostic.html` $12k · `commercial.html` $30k). Rebuilds of annex/archive/books/claims kept those doors; the stale exact list failed 8 assertions. Reproduced on current main after #14936.

Sibling KEEP-pin / MANUAL.md leftovers from that same run were already lifted by later TYPE/NEWBOT/LATCH work. Unique leftover still red: this exact-href contract.

## Repair
Keep exact href equality. Expand the expected list to Autopsy/$199 + Larger fixed in snippet order. Assert Larger fixed copy. Do not strip product doors. No invented Stripe.

## Paths
- `test_board_cash_rebake.py`
- `p/grok-board-cash-rebake-larger-fixed-20260916-01.md`

## Collision fence
≠ newbot-01..17 ≠ Type battery/autopsy KEEP ≠ Latch MANUAL canary ≠ coil-manual ≠ Goat/Quill/Wire#14898/Ink/DJ/Admin/Bass/Moth/Reed/Spy

Tip KEEP. Hands off #8802. No PUT ingest.

## Cite
`grok-board-cash-rebake-larger-fixed-20260916-01`

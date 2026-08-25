# SUBZERO receipt — quote-draft bind, not buyer acceptance

Slack `1787650230.035359` (2026-08-25), JOJO BACKEND CELL **H-008**,
plus Slack `1787651030.360809` JOJO **SECOND PASS** on squash
`5d796079`:

> source-index the existing `sz-paid-validation` / P01 `$2,500`
> offer into the smallest honest quote-draft → buyer-bound
> validation receipt implementation packet.

That Slack body is **CLAIMED** for this leftover. Quote draft
already landed: `p/rivet-ship-subzero-quote-20260825-01.md`.
First receipt leftover already landed:
`p/rivet-ship-subzero-receipt-20260825-01.md`. Do not remint.
Human-outcomes already landed via `#2324`. Peer `#2320`
grok-receipt stays peer-owned.

Talk is not a land.

## Unique leftover (this run)

The first bind treated any `p/{id}.md` as `BUYER_BOUND`, used
the project's own quote receipt as `buyer_id`, let
`..\\ground\\EXECUTE` escape `p/` on Windows, coerced missing
numerics to `0`, refused caller `PASS` only for hard-coded
GRBN, and framed titan `NOT_WRITTEN` as a leftover lock.

This leftover closes those holes. Slack `1787651639.893089`
then named the remaining ones: a semantically relevant public
inbound is required (IRRELEVANT_INBOUND / SELF_BIND are not
inbound_ok); Windows path escape is rejected, not stripped;
missing numeric never coerce; leftover INTEGRATED is not a
legal quote state. Honest facts stay: `$2500`, `QUOTE_DRAFT`,
`STRUCTURAL_ONLY`, demand `UNKNOWN`, cash `$0 / NOT_LANDED`.
The live binder stays **CANDIDATE / INCOMPLETE / NEEDS_BUYER**.
That is not buyer acceptance and not cash readiness.

`inbound_rel()` canonicalizes one post id, forbids `/` and `\`,
and proves the resolved path stays exactly under `p/`. File
existence is not acceptance. `SELF_BIND` refuses the project's
own quote / first-receipt / human-outcomes ids. Missing
numerics are `UNRESOLVED` / `FINDER-FAILED`, never coerced to
`0`. Receipts carry source commit/tree, quote hash, catalog-row
hash, fab/test/card/sidecar hashes, request hash, and
`delivery_hash=UNRESOLVED`. Legal states are
`DRAFT → NEEDS_BUYER → ACCEPTED → DELIVERED`. Caller `PASS` is
refused on every excerpt unless legal state is `ACCEPTED`.

Source-index (read, not reminted):

- SKU `sz-paid-validation`
- P01 `P01_catalog_receipt`
- price `$2500` (inside P01 $1500–$3000)
- leftover class `QUOTE_DRAFT`
- GTM status `CANDIDATE`
- schema `buyer_receipt` / `SUBZERO_BUYER_VALIDATION`

A bind function is not a buyer. A public post id is not a seat.
Possessing the link is authorization. Blank `from=` still lands
as `UNSEATED`.

## Occupied cash doors (do not remint)

| SKU | Price | File |
|---|---|---|
| `white-box-gguf-pilot-30d` | $30,000 / 30d | `commercial.json` |
| `gguf-diagnostic-10d-12k` | $12,000 / 10d | `revenue/payment_ready/pack.json` |

`sz-paid-validation` does not join those doors. This leftover
does not contact buyers, open accounts, or store private data.

## Measure

Instrument: `host/subzero_receipt.py`. Door: `subzero-receipt.html`.
Stdlib only. Catalog: `ground/SUBZERO_RECEIPT.json`.
It reads the tree. It does not smash `commons.mno`. It does not
add a gate. It does not open accounts. A titan-untouched brag
is a skipped lane, not a leftover lock.

```bash
python3 host/subzero_receipt.py
python3 host/subzero_receipt.py --root .
python3 host/subzero_receipt.py --self-test
python3 -m unittest -v test_subzero_receipt.py
```

X = exact files in SEARCH_SPACE
Y = sku + P01 + $2500 + closed bind holes + CANDIDATE/INCOMPLETE
    + NEEDS_BUYER + cash $0 PRESENT + demand UNKNOWN +
    runtime_proof false + hashes
Z = missing leftover / invented buyer / cash-runtime-demand claim /
    FINDER-FAILED
Miss is **FINDER-FAILED** / **FINDER-UNVERIFIED**, never `0`.

JOJO H-008 / second-pass / quote-draft bind talk without this
leftover is **CLAIMED**. Missing card / catalog / door /
source-index is **NOT_LANDED**. Census + open door is
**INTEGRATED**. Live binder stays CANDIDATE/INCOMPLETE. A Slack
body is still not the file.

Do not remint SUBZERO_QUOTE / SUBZERO_TECH / SUBZERO_GTM /
SUBZERO_BUYERS / SUBZERO_EXPLORER / SUBZERO_PROOF / White Box /
`rivet-ship-subzero-quote-20260825-01` /
`rivet-ship-subzero-receipt-20260825-01`. Hands off CML PR 2108,
grok-receipt PR 2320, human-outcomes, SPECTER. No auth. No gate.

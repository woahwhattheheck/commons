# SUBZERO receipt — quote-draft → buyer-bound, not cash

Slack `1787650230.035359` (2026-08-25), JOJO BACKEND CELL **H-008**:

> source-index the existing `sz-paid-validation` / P01 `$2,500`
> offer into the smallest honest quote-draft → buyer-bound
> validation receipt implementation packet.

That Slack body is **CLAIMED** for this leftover. Quote draft
already landed: `p/rivet-ship-subzero-quote-20260825-01.md` on
`1ab2e560636566bf38c2ce199fd5a70b341b910b`. Human-outcomes
already landed via `#2324`. Peer `#2320` grok-receipt stays
peer-owned. Do not remint those lanes.

Talk is not a land.

## Unique leftover (this run)

SUBZERO_QUOTE already named `sz-paid-validation` as
**QUOTE_DRAFT** $2500. SUBZERO_GTM already named the SKU as
**CANDIDATE**. SUBZERO_BUYERS already named `P01_catalog_receipt`
($1500–$3000). Explorer v2 already landed
`validation_receipt.schema.json`. Do not remint those desks,
White Box, payment-ready, human-outcomes, or grok-receipt.

The next fact those leftovers left open: **a quote draft becomes
a buyer-bound STRUCTURAL_ONLY receipt only when a public inbound
post names a file.** The bind is implemented. Live bind stays
**UNBOUND**. Demand stays **UNKNOWN**. Cash stays **$0 / NOT_LANDED**.

Source-index (read, not reminted):

- SKU `sz-paid-validation`
- P01 `P01_catalog_receipt`
- price `$2500` (inside P01 $1500–$3000)
- leftover class `QUOTE_DRAFT`
- GTM status `CANDIDATE`
- schema `buyer_receipt` / `SUBZERO_BUYER_VALIDATION`

Bind rules:

- `buyer_id` is a public inbound `p/{id}.md`, not a private identity
- named excerpt + SHA-256 + magic/LE header
- `bound=true` only when both exist
- live PASS is refused (that would claim CUSTOMER_READY)
- bound is still `STRUCTURAL_ONLY`
- missing inbound stays `UNBOUND`

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
It reads the tree. It does not write titan. It does not smash
`commons.mno`. It does not add a gate. It does not open accounts.

```bash
python3 host/subzero_receipt.py
python3 host/subzero_receipt.py --root .
python3 host/subzero_receipt.py --self-test
python3 -m unittest -v test_subzero_receipt.py
```

X = exact files in SEARCH_SPACE
Y = sku + P01 + $2500 + bind implementation + UNBOUND + cash $0 +
    demand UNKNOWN + runtime_proof false
Z = missing leftover / invented buyer / cash-runtime-demand claim /
    FINDER-FAILED
Miss is **FINDER-FAILED** / **FINDER-UNVERIFIED**, never `0`.

JOJO H-008 / quote-draft → buyer-bound / validation-receipt
talk without this leftover is **CLAIMED**. Missing card / catalog /
door / source-index is **NOT_LANDED**. Census + open door is
**INTEGRATED**. A Slack H-008 body is still not the file.

Hands off CML PR 2108, grok-receipt PR 2320, human-outcomes,
SPECTER, titan `--go`. Do not remint SUBZERO_QUOTE /
SUBZERO_TECH / SUBZERO_GTM / SUBZERO_BUYERS / SUBZERO_EXPLORER /
SUBZERO_PROOF / White Box / `rivet-ship-subzero-quote-20260825-01`.
No auth. No gate. titan: **NOT_WRITTEN**.

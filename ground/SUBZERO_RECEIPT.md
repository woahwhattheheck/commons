# SUBZERO receipt — quote-draft → buyer-bound validation receipt, not cash

Slack `1787650230.035359` (2026-08-25), JOJO BACKEND CELL **H-008**
landed the first binder. Slack `1787650970.236559` /
`1787651030.360809` (**H-009** + second-pass audit) measured
concrete defects on squash `5d79607990fb1493464940a5763a658742a230fd`
/ source tree `0509da3e5be25020433bfdeb8883fc6fc97e8986`. This
leftover hardens that same binder. Do not remint H-008 or
`rivet-ship-subzero-receipt-20260825-01`.

Talk is not a land.

## Unique leftover (this run)

The H-008 bind existed. The audit found it was not buyer-bound:

- `inbound_rel` rejected `/` but not Windows `\`, so
  `..\ground\EXECUTE` escaped `p/`
- any existing `p/{id}.md` counted as `BUYER_BOUND`; the
  self-check used the project's own quote receipt as `buyer_id`
- missing numeric fields coerced to `0`
- no quote hash / source tree / request hash / legal transitions
- `PASS` refused only for hard-coded GRBN
- titan `NOT_WRITTEN` / hands-off framing treated as a lock

Those defects are closed here. Live bind stays **UNBOUND**.
Demand stays **UNKNOWN**. Cash stays **$0 / NOT_LANDED**.
Missing numbers stay **UNRESOLVED** / **FINDER-FAILED**, never a
silent 0.

A **project receipt is not a buyer**. **File is not acceptance**.
`BUYER_BOUND` needs a canonical inbound id, a distinct claim,
acceptance subject/body, the quote hash, and a named excerpt.

Legal states: `DRAFT` → `NEEDS_BUYER` → `ACCEPTED` → `DELIVERED`.
Live legal state stays `DRAFT`.

Source-index (read, not reminted):

- SKU `sz-paid-validation`
- P01 `P01_catalog_receipt`
- price `$2500` (inside P01 $1500–$3000)
- leftover class `QUOTE_DRAFT`
- GTM status `CANDIDATE`
- schema `buyer_receipt` / `SUBZERO_BUYER_VALIDATION`

Bind rules:

- `buyer_id` is a public inbound `p/{id}.md`, not a private identity
- inbound id is `[A-Za-z0-9._-]{8,80}`; both separators and
  traversal are refused; resolved path stays under `p/`
- named excerpt + SHA-256 + magic/LE header
- `bound=true` only with acceptance + quote hash
- live PASS is refused on every excerpt (that would claim
  CUSTOMER_READY)
- bound is still `STRUCTURAL_ONLY`
- missing inbound stays `UNBOUND`

A bind function is not a buyer. A public post id is not a seat.
Possessing the link is authorization. Blank `from=` still lands
as `UNSEATED`. Open door. No auth. No gate.

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
add a gate. It does not open accounts. It does not treat titan
stillness as an accomplishment.

```bash
python3 host/subzero_receipt.py
python3 host/subzero_receipt.py --root .
python3 host/subzero_receipt.py --self-test
python3 -m unittest -v test_subzero_receipt.py
```

X = exact files in SEARCH_SPACE
Y = sku + P01 + $2500 + inbound-id + UNRESOLVED missing fields +
    quote hash + source tree + UNBOUND + cash $0 + demand UNKNOWN
Z = missing leftover / invented buyer / cash-runtime-demand claim /
    FINDER-FAILED
Miss is **FINDER-FAILED** / **FINDER-UNVERIFIED**, never `0`.
Never 0.

JOJO H-009 / #2329 second-pass / binder-not-buyer-bound talk
without this leftover is **CLAIMED**. Missing card / catalog /
door / source-index is **NOT_LANDED**. Census + open door is
**INTEGRATED**. A Slack H-008 / H-009 body is still not the file.

Do not remint SUBZERO_QUOTE / SUBZERO_TECH / SUBZERO_GTM /
SUBZERO_BUYERS / SUBZERO_EXPLORER / SUBZERO_PROOF / White Box /
`rivet-ship-subzero-quote-20260825-01` /
`rivet-ship-subzero-receipt-20260825-01`. Peer-owned: PR 2320,
PR 2325, PR 2328. No auth. No gate.

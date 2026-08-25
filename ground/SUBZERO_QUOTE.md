# SUBZERO quote — sz-paid-validation is a draft, not cash

Slack `1787649732.551439` (2026-08-25), JOJO:

> Commercial consequence: `sz-paid-validation` remains a $2,500
> quote draft over STRUCTURAL_ONLY evidence—not runtime, demand,
> or cash proof.

That Slack body is **CLAIMED** for this leftover. Presence already
landed: `p/rivet-ship-subzero-tech-presence-20260825-01.md` on
`5e8f3b6e6f4499ebf6ec1c6478c1554a296c2986`. Do not remint it.

Talk is not a land.

## Unique leftover (this run)

SUBZERO_TECH already named Titan file presence as **PRESENT** and
`runtime_proof=false`. SUBZERO_GTM already named
`sz-paid-validation` as a **CANDIDATE** $2500 path. SUBZERO_BUYERS
and Explorer/Proof already refuse presence-as-runtime. Do not remint
those desks, White Box, payment-ready, or human-outcomes.

The next fact those leftovers left open: **a $2500 SKU over
STRUCTURAL_ONLY evidence is a quote draft, not cash, not demand,
not runtime.**

Measured commercial consequence:

- SKU `sz-paid-validation`
- price `$2500`
- GTM status `CANDIDATE`
- leftover class `QUOTE_DRAFT`
- evidence `STRUCTURAL_ONLY` (structural=31, runtime=0, customer=0)
- `titan_presence_is_runtime_proof=false`
- collected cash `$0 / NOT_LANDED`
- demand `UNKNOWN`

A quote draft is not a deposit. A presence file is not a runtime
receipt. A catalog SKU is not inbound demand.

## Occupied cash doors (do not remint)

| SKU | Price | File |
|---|---|---|
| `white-box-gguf-pilot-30d` | $30,000 / 30d | `commercial.json` |
| `gguf-diagnostic-10d-12k` | $12,000 / 10d | `revenue/payment_ready/pack.json` |

`sz-paid-validation` does not join those doors until an independently
evidenced buyer, payout dest, and STRUCTURAL_ONLY delivery receipt
exist. This leftover does not create them.

## Measure

Instrument: `host/subzero_quote.py`. Door: `subzero-quote.html`.
Stdlib only. Catalog: `ground/SUBZERO_QUOTE.json`.
It reads the tree. It does not write titan. It does not smash
`commons.mno`. It does not add a gate. It does not open accounts.

```bash
python3 host/subzero_quote.py
python3 host/subzero_quote.py --root .
python3 host/subzero_quote.py --self-test
python3 -m unittest -v test_subzero_quote.py
```

X = exact files in SEARCH_SPACE
Y = sku + $2500 + QUOTE_DRAFT + STRUCTURAL_ONLY + cash $0 +
    demand UNKNOWN + runtime_proof false
Z = missing leftover / cash-runtime-demand claim / FINDER-FAILED
Miss is **FINDER-FAILED** / **FINDER-UNVERIFIED**, never `0`.

JOJO commercial-consequence / `sz-paid-validation` / quote-draft
talk without this leftover is **CLAIMED**. Missing card / catalog /
door is **NOT_LANDED**. Census + open door is **INTEGRATED**. A
Slack commercial consequence is still not the file.

Hands off CML PR 2108, JOJO README PR 2286, SPECTER, titan `--go`.
Do not remint SUBZERO_TECH / SUBZERO_GTM / SUBZERO_BUYERS /
SUBZERO_EXPLORER / SUBZERO_PROOF / White Box / human-outcomes /
`rivet-ship-subzero-tech-presence-20260825-01`. Possessing the
link is authorization. Blank `from=` still lands as `UNSEATED`.
No auth. No gate. titan: **NOT_WRITTEN**.

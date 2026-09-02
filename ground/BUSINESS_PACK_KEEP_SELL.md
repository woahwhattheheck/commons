# KEEP vs SELL factory

`#business-packs` `C0BU7JAPUH3` is the KEEP / SELL factory lane. This card is
the machine ledger for those decisions. It is not the pack-scaffold landing
and it does not steal that GOAT PR.

Cite the control-plane map: [SLACK_CONTROL_PLANE.md](./SLACK_CONTROL_PLANE.md).
Receipt already on main: `cursor-slack-business-packs-channel-20260902-01`.
Do not remint that id.

Uniqueness / similar-is-not-clone / mystery-nuts law already lives on
[BUSINESS_PACKS.md](./BUSINESS_PACKS.md) and [business-packs.html](../business-packs.html).
Candidate loader is `host/pack_keep_sell_candidate.py`. This factory does
not remint those files.

## Product

Build revenue-capable businesses cheap. Keep the winners. Sell the rest as
packages with assets plus instructions.

## Rules

- Marketing stays with Bryce. This tool cannot assign ads, spend, or a
  marketing peer.
- No invented Stripe URLs. Owner pastes a live Payment Link. The public door
  never turns a stored URL into `<a href>` unless checkout capability already
  marks that exact link CHARGEABLE.
- Tiers named in-channel: `$20` `$100` `$200` `$1,000` consumer / lower;
  `$10,000` SMB. A named tier is not a chargeable checkout.
- Sellable product engines land on the matching private product `main`.
  This public ledger is the KEEP / SELL factory, not the engine.
- Cash stays `USD 0` until an independently evidenced `BANK_AVAILABLE` event.
  Buyers stay `0` until a receipt.

## Decisions

| Decision | Meaning |
| --- | --- |
| `OPEN` | named pack, no KEEP / SELL yet |
| `KEEP` | we keep operating it |
| `SELL` | package it (assets + instructions) for sale |

Work posts and KEEP vs SELL decisions live in `#business-packs`.

## Measure

```bash
python3 host/business_pack_keep_sell.py validate
python3 host/business_pack_keep_sell.py list
python3 host/business_pack_keep_sell.py --self-test
python3 -m unittest -v test_business_pack_keep_sell.py
```

Human door: [keep-sell.html](../keep-sell.html)
Machine: [BUSINESS_PACK_KEEP_SELL.json](./BUSINESS_PACK_KEEP_SELL.json)

Open door. No auth. No secrets.

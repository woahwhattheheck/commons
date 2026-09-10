# TITAN V3 L01 day-zero engine-grammar closure

**Disposition: reject `l01_day0buy` as shipped; preserve the canonical step-0 `BUY_PRODUCT WHEAT 13` action.**

This is an additive, source-bound repair and evidence carrier for `TITAN-V3-L01-DAY0-ENGINE-GRAMMAR-CLOSURE-20260910-01`. It does not publish a new canonical archive, change `TITAN-CONFIG.json`, enable a feature, submit to Kaggle, or claim that the stale one-tree packet is current. The one-tree publisher retains integration, rebuild, panel, merge, promotion, provider, and submission custody.

## Exact source closure

The authenticated Slack object `F0C0JPCAAQP` is 27,500 bytes with SHA-256 `f68792bf7f0fb269864ef4ab25967292e2d4cd03439dbc5c52b98dfcebd1b728`. Its `overlay/l01_mechanics.py` preimage is SHA-256 `65fc1841f6d00b6db78e2eb88d98e9e7b05053502e0de527bce1f1a60fbe9691`; the packet manifest binds base archive `a055fd56ca5821208096f37787f77dbdddc2f65c14c24132d6e219a05e6f02ba` and route tape `7015cc00acfa4922`. `SOURCE-PACKET-WITNESS.json` and `source_packet_witness.py` close those identities without extracting the archive.

The packet is separately held as a stale re-pin. That transport defect does not weaken this source theorem: the exact L01 source itself creates six step-0 rows, all using `BUY_PRODUCT`, for CARROT 14, MELON 20, MILK 40, STRAWBERRY 8, TOMATO 12, and WHEAT 2.

## Source-real defect

The pinned official interpreter accepts `BUY_PRODUCT` only for WHEAT and FERTILIZER. Crop planting inventory must be acquired through `BUY_SEED`; MILK has no purchase operation. Consequently, five of the six generated rows abort as unsupported sub-operations. The only executable row purchases WHEAT 2, replacing the canonical WHEAT 13 purchase.

`official_engine_witness.py` reads the three engine members from `exports/titan-current.tar.gz`, verifies their exact hashes, and runs a one-turn two-player interpretation with a PASS rival. The result is deterministic:

| Action | Money after step 0 | Shed WHEAT | Public WHEAT inventory |
|---|---:|---:|---:|
| Canonical WHEAT 13 | 2,643 | 13 | 9,986 |
| Shipped L01 basket | 2,948 | 2 | 9,997 |

The feature therefore removes 11 units of the route's intended opening WHEAT. It is not an executable SpaTaro basket.

## Score-facing diagnostic

`L01-DAY0-PANEL.json` preserves a 4-seed × 2-seat matched diagnostic against Arlene using the transferred predecessor archive `6ac897241cb54baa205e4132fab1f83e7a21e4ae957e19e16c6c48a7ecbd8bc1`. That archive is not current-one-tree promotion evidence; it is used because it carries the same documented MAIN tape and exact day-zero transform.

All eight candidate-seat action traces changed. Every control win became a loss. Mean margin delta was **−16,688.25**, median **−16,945.5**, with all eight cells negative and a range of −28,353 to −4,509. Two cells lost 30,398 own cash. Six cells increased own cash, producing a misleading positive mean own delta of +9,518.75, while the rival gained even more; this is why outcome and margin custody are mandatory.

## Repair contract

`L01-DAY0-GRAMMAR.patch` is a minimal patch against the authenticated source preimage. It:

- validates the static day-zero rows against the pinned `BUY_PRODUCT` item grammar;
- rejects malformed rows, noncanonical quantities, and rows beyond the executable prefix;
- emits one deterministic `L01_noop:day0buy_rejected[...]` reason;
- leaves the route tape byte-behavior unchanged and records no activation on rejection;
- retains exact all-flags-off identity and alias/idempotence behavior.

The standalone `l01_day0_guard.py` is a stricter reusable admission primitive. A future replacement also needs explicit per-unit price ceilings before it can claim a starting-cash solvency bound. This carrier intentionally does not invent a corrected leader basket: changing verbs or quantities creates a new opening hypothesis that needs its own source, budget, returned-action, and matched-game evidence.

## Reproduction

From this directory:

```bash
python -m unittest -v test_l01_day0_guard.py test_receipts.py
TITAN_ARCHIVE=../../../exports/titan-current.tar.gz \
  python -m unittest -v test_official_engine_witness.py
python official_engine_witness.py \
  --archive ../../../exports/titan-current.tar.gz
python source_packet_witness.py /path/to/v3_candidates_657b3d9c.tar.gz
```

Focused local evidence at publication: 15 guard contracts, 5 exact-engine contracts, 6 patch-predecessor contracts, and 4 durable-receipt contracts passed. No network, owner-PC compute, provider call, Kaggle write, or canonical-tree mutation is required.

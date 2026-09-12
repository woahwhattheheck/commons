# TITAN V5 fertilizer-floor arbitrage current ABI

`TITAN-V5-FERT-FLOOR-ARBITRAGE-CURRENT-ABI-REAUTHOR-WIDE` is a fresh current-V5 re-author, **not** a recovery of the lost `r04_fert_arbitrage` payload.

## Durable authority

The source-real mechanic is already merged and corrected in the repository:

- mechanism research PR: #13057;
- corrected follow-up commit: `d8fa49ccbedf2a51c65431bae51a7f99e648da20`;
- current `fert_floor_apply.py` Git blob: `a32160a2298e9d92a824b52bc272535583a85a67`.

That work proves the official interpreter path `BUY_PRODUCT FERTILIZER -> shed -> PICKUP -> FERTILIZE -> WATER -> legal HARVEST -> sale`. It does **not** prove current-route reachability or promotion.

The historical replay receipt that motivated this re-author reported one positive policy family only: the strict observed buy-price `2` / floor-entry configuration. The high-price trigger was strongly negative and is intentionally absent here. Historical uplift is motivation only; it is not accepted as current-V5 evidence.

## Current ABI theorem

The adapter is selected-action-only and never invokes or mutates a producer/controller.

It may do exactly two things:

1. **Floor acquisition:** append one `BUY_PRODUCT FERTILIZER 1` only when the public current FERTILIZER quote is exactly `2`, money and a market slot are available, the farm owns no fertilizer in shed or actor inventory, no existing parent market row mentions fertilizer, and a live plant exists that is not already covered through the current fertilizer window.
2. **Application:** replace only a literal actor `PASS` with `FERTILIZE` when that same actor already carries fertilizer and is standing on an eligible live plant.

It never invents `PICKUP`. That is deliberate: if current V5 does not naturally move bought fertilizer from shed to a worker, engagement should be zero and this candidate should die rather than grow a second route/controller.

Malformed observation/action/cardinality/inventory/price/config evidence fails closed. Inputs are deep-copy safe; non-PASS parent commands are never overwritten.

## Natural-engagement receipt

`fert_floor_engagement.py` consumes a source-bound ordered tape of **real returned actions plus the next public observation**. A returned command by itself is not engagement. The receipt becomes `engaged=true` only after one full naturally executed chain is confirmed from public custody transitions:

1. returned strict-price-2 `BUY_PRODUCT FERTILIZER 1`, followed by exactly one unit arriving in shed custody;
2. parent-returned `PICKUP FERTILIZER`, followed by that same unit leaving shed and entering one actor inventory;
3. parent-returned `FERTILIZE` by that same actor on an eligible live plant, followed by one unit being consumed and the crop's `fertilized_until_day` increasing to the official window.

The tape must be contiguous for one player and binds exact `source_sha`, `engine_id`, and a canonical SHA-256 over the rows. A second fertilizer market action during an active chain makes provenance ambiguous and aborts that chain. Non-floor buys, unrelated pickups, failed commands, skipped callbacks, player changes, malformed cardinality, and unconfirmed engine effects cannot produce engagement.

This receipt authorizes **only the next evidence spend**. It is not an economics, promotion, or activation receipt.

## Promotion path

This directory is research/source only. It makes no runtime/default/TITAN-CONFIG/CURRENT/archive/release/Kaggle changes.

Before any integration or activation:

1. authenticate the exact current V5 selected-action/source identities consuming this adapter;
2. obtain a natural-engagement receipt proving price-2 acquisition -> real pickup custody -> official fertilizer effect;
3. require matched OFF/ON both-seat economics against current V5 and the exact V3.1 champion floor;
4. reject promotion if the only positive cells rely on constructed idle callbacks or if displaced current actions dominate the fertilizer gain.

## Focused contract

```bash
python -B -m py_compile \
  fert_floor_current.py fert_floor_engagement.py \
  test_fert_floor_current.py test_fert_floor_engagement.py
python -B -m unittest -v \
  test_fert_floor_current.py test_fert_floor_engagement.py
python -O -B -m unittest -v \
  test_fert_floor_current.py test_fert_floor_engagement.py
```

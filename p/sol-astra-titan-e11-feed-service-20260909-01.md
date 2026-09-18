# SOL-ASTRA — TITAN V2.5 E11 feed-service evaluator

Operation: `titan-v25-orders-20260909-E11`
Worker lane: `sol-astra-titan-e11-feed-service-20260909-01`

## Collision / base receipt

- Exact E11 Slack thread was read before claim and had zero replies.
- Exact workspace search for `titan-v25-orders-20260909-E11` returned only the
  parent work order.
- Claimed publicly in `#titan-v25-sim-runs` before source mutation.
- Fresh Commons base at claim:
  `e5e1dae66cbc3c4b1e3399fbf93b63e1edf8066d`
- Base tree:
  `f2face0b6bf35064b33c11198e2f5a838e6e23f0`
- Fresh Commons publication base after concurrent merges:
  `ec083c2feb41c944dbf76481c50f5f0c6817569e`
- Publication base tree:
  `22fb30347182da8a57c939495b020103ed43c137`
- All five owned destinations were re-read at that publication base and returned
  404 before any blob/tree/commit mutation.

## Source finding

Current `operating_stock.py` already contains `protect_feed_stock`, and
`titan_runtime.py` applies it at the final returned-action boundary when
`operating_stock=true`. That path protects owned WHEAT for producer-authored
feeds. It explicitly raises `unresolved_wheat_replenishment` for
`BUY_PRODUCT WHEAT`, and `test_feed_stock.py` contains current/future requested
purchase cases that must remain uncertified. Therefore E11 is not a missing
retention rule; its distinct unresolved seam is procurement + actual receipt
timing.

## Owned paths

Additive only:

- `revenue/kaggriculture/cloud-economic-stress/feed-service-economics/README.md`
- `revenue/kaggriculture/cloud-economic-stress/feed-service-economics/feed_service_economics.py`
- `revenue/kaggriculture/cloud-economic-stress/feed-service-economics/test_feed_service_economics.py`
- `.github/workflows/titan-e11-feed-service.yml`
- `p/sol-astra-titan-e11-feed-service-20260909-01.md`

Explicitly not owned or modified: canonical `frozen_selected.py`,
`operating_stock.py`, `titan_runtime.py`, `selected_sell_core.py`, release
pointers/manifests, archive bytes, or Kaggle submission state.

## Evidence contract

The evaluator must retain actor-before-market timing, exact unitwise WHEAT buy
impact, partial fill under cash/capacity, full actual pickup consumption across
competing actors, escape deadlines, terminal payback, no future-sale cash
credit, and strict no-op when inherited service is best. Any later canonical
activation requires the 64-game matched E11 development screen and untouched
holdout; this additive publication makes no score-gain claim.

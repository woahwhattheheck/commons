# TITAN V4 Gemini salvage / convergence ledger

Status: research/convergence authority only. This file does not create a second V4,
controller, release key, default, archive, evaluator, provider, or Kaggle package.

This ledger records the Gemini-origin families recovered from Slack and GitHub through
2026-09-12 01:00 ET and routes each one into the **single existing V4 authority** in
its strongest source-grounded form. The rule is: preserve the idea, discard weaker
heuristics, falsify bad premises durably, and never fork an already-owned seam.

## Convergence table

| Gemini origin | Original idea | Best V4 form | Disposition / authority |
|---|---|---|---|
| G01 / E11 | Rival-aware SELL deferral | Deterministic town-drain premium + public rival-supply lower bound + queue/custody/funding/row-budget/horizon guards; no generic retimer | `research/market-baseline/`; `town_sale_deferral.py`, `TOWNSELL-CURRENT.md`, `gemini_market_certificate.py` |
| G01 / O01 | Rival archetype model | Observable public behavior only: proved prior net supply, same-row collision/crossflow, town drain. No opponent-ID/static classifier | `research/market-baseline/`; B10 public-supply lineage + COBUY/CROSSFLOW + Gemini certificate |
| G01 / E20 | Drop a late low-value HIRE | Current executable-prefix semantics + exact wage/cash + labor/service frontier; never reason over engine-inert suffix rows | Existing E20 executable-prefix lineage and current labor/service owners; do not recreate G01 guard |
| G01 / SHOP_ARB | Fixed shop-absorption weight | Source-bound town demand timing and shop/RNG observables; only retime already-required actions after replay | `research/market-baseline/` (TOWN-WHEAT/TOWNSELL) and SHOPSTREAM research; old 1.5x heuristic retired |
| S33 / STRATUM | Rank SELLs by projected shed relief | Canonical `row-shed-sell-order` plus novelty guard: identity when STRATUM rank duplicates canonical pressure rank, preserve only distinct rank | `repairs/gameplay/row-shed-sell-order/`; no sibling row-shed package |
| Gemini Pro capital | Earlier capital/service acquisition | Current `early-capital` authority with executable lockstep/custody checks; KESTREL only admits safe reordering behind capital | `repairs/gameplay/early-capital/` |
| Gemini Flash market / GOOP | Joint slot composition and market timing | Prefix-aware, order-budget-safe market research; COBUY/CROSSFLOW/TOWNSELL/TOWNFLASH evidence before any owner consumption | `research/market-baseline/` + existing prefix/order-budget owners |
| Gemini idle hands / FEED / CARE | Spend otherwise-idle service capacity | Starvation/dead-service activation with explicit custody and EOD need; do not mint another service key | `repairs/gameplay/dead-feed-care/` plus existing feed/recycle owners |
| Gemini goose acquisition/service | Add geese where downstream service/value exists | Current goose cap/EOD rescue lineage with executable-prefix and carrying-capacity checks | Existing H3 goose owners; evidence consumer only |
| Gemini WHEAT/FERT | Buy/route WHEAT or use idle labor to improve fertilizer/feed economy | Existing WHEAT starvation-unlock and fertilizer service/ROI families; preserve only source-backed marginal ROI | Existing F2/S1/S6/fert-hand authorities; no parallel controller |
| Antigravity FERT | Sell surplus FERT / treat floor sale as warehouse | **Split result:** useful surplus-sale/capacity idea converges into existing FERT seller/B7; recoverable warehouse premise is falsified | `repairs/gameplay/b7-shed-overflow/`; `research/mechanism-claims/CLAIMS.json`; deleted duplicate `antigravity-fert-warehouse` path must stay dead |
| Antigravity MELON | Reserve committed + held + planted max yield before planting more MELON | Aggregate proposal-budget/custody cap, fail closed on malformed state | `repairs/gameplay/antigravity-melon-cap/` |
| Gemini top-agent / Apex dump | Clone radar, scheduled front-running, protected fertilizer cash, projected-shed relief, shop micro-batching, crop-maturity ambush, staged liquidation | Decompose into public/source-bound market, capacity, cash-reserve and endgame authorities; external opponent schedule is hypothesis, not source truth | `research/market-baseline/COUNTER_AMBUSH*`, TOWNSELL, row-shed, existing reserve/endgame owners |
| Gemini shop-stream follow-up | Occupancy can shift shop unlock because weed RNG is consumed before shop RNG | Keep as source-bound RNG research until an observable/current-native predictor has positive economics | Research only; no runtime policy from occupancy→shop inference yet |

## New E11/O01 strengthening: `gemini_market_certificate.py`

The old G01 E11/O01 pair is retained only as ancestry. The V4 replacement uses a
conservative public theorem for one product between consecutive callbacks:

```text
delta_inventory = own_sell + rival_sell - own_buy - rival_buy - town_consume

rival_sell - rival_buy
  >= current_inventory - previous_inventory
     + town_consume - own_sell_requested_upper_bound
```

A positive lower bound proves **already-realized prior rival net supply**. A
non-positive bound proves nothing about rival inactivity. This is intentionally
stronger than an archetype label because it is an observable certificate with an
explicit one-way inference.

`sell_deferral_replay_certificate()` then requires all of the following before it
even returns `CANDIDATE_FOR_OWNER_REPLAY`:

- an already-existing SELL (the certificate cannot create one),
- positive deterministic town-drain premium,
- complete evidence,
- queue safety,
- custody safety,
- financing safety,
- row-budget safety,
- horizon safety,
- and no *proved* prior rival net-supply lower bound.

Even then `policy_authorized` remains `false`; current-native owner replay is still
mandatory. Positive prior rival supply returns a conservative veto rather than the
old E11 guess that waiting is attractive.

## S33 strengthening: preserve only novel rank information

The current V4 row-shed work found the useful and harmful cases separate cleanly:
the harmful late case reproduced the same order as the already-enabled pressure
rank, while the large positive case introduced a distinct rank. Therefore the
strong form of Gemini S33 is not “always apply projected-shed rank”; it is:

1. compute canonical pressure rank,
2. compute STRATUM/projected-shed rank,
3. if identical, return exact parent identity,
4. if distinct, permit STRATUM only inside the existing row-shed authority,
5. missing/malformed pressure evidence fails closed to identity.

Current Slack evidence reported an 8-seed x both-seat mirror improving from mixed
(mean +63.875, min -21) to a novelty-guard prototype with mean +68.125, min 0,
max +410, 6 positive / 10 identity / 0 negative. That result belongs in the
existing row-shed owner; this ledger intentionally does not duplicate its source.

## Explicit do-not-repeat premises

- **FERT floor sale is not a recoverable warehouse.** SELL consumes shed stock but
  does not add the sold unit to public market inventory. The Antigravity warehouse
  premise is falsified and recorded in mechanism claims; B7 remains the capacity
  relief authority.
- **Do not classify opponents by identity/archetype** when a public-state bound can
  express the behavior directly.
- **Do not hardcode an Apex/Gemini step schedule** as engine truth. Shop multiset,
  inventory, queue state and public market flow determine whether the timing has
  value.
- **Do not scan non-executable market suffix rows as if they execute.** E20 and all
  descendants must respect the official executable prefix.
- **Do not add a second authority** for row-shed, FERT disposal, dead FEED/CARE,
  early capital, or market-baseline timing.

## Next gates

1. Existing row-shed owner: consume the novelty guard and run current field materialization.
2. Market seller owner: feed `gemini_market_certificate.py` with current-native
   TOWNSELL witnesses and public-supply transitions; census replay candidates and
   vetoes before proposing any runtime consumer.
3. Antigravity MELON owner: current-native reachability/economics only; source already exists.
4. SHOPSTREAM: prove observability and current-native economic effect before policy.
5. Any newly recovered Gemini post must be appended here and routed to an existing
   authority before a new package/key is considered.

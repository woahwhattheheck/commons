# KAG-COMPILED-CONTEXT

A new deterministic daily plan/context controller, composed with the exact selected
`cloud-composition/candidate.py` (`dispatch_balanced`). The standalone generated
`candidate.py` runs offline with Python's standard library. No model, inference,
weight baking, hidden seed, future shop inspection or public replay script.
The pinned baseline hash is enforced by `build.py`. Peer scheduling source is intact.

This is an experimental policy component, **not the selected TITAN submission**.
Initial v1 paired development games lost to dispatch_balanced by 16,263 cash in
both seats on seed 9300101 (41,179 vs 57,442); both games completed. See raw results.
Seven focused contract checks passed. No winning-agent or hosted-Kaggle claim.
The next experiment will address an overly conservative daily worker budget and
installation quota, using this failed candidate as retained evidence.

## Interface

- `select_context(obs, configuration=None) -> dict`: own cash, stock (shed plus
  carried), feed, workers, capacity, inclusive remaining actions, crop/animal
  first-production feasibility and return distance. No future shops or RNG.
- `advance(obs, configuration=None, previous=None, options=None) -> dict`: persistent
  JSON state with fixed daily targets, phase, reserves, backlog, observed outcomes,
  completion and expiry counts, at most eight feedback/bank entries. Reset on seat
  change or decreasing step; same-step calls are idempotent. The caller must clear
  state for a new game when the first step is indistinguishable from a prior step.
- `constrain_orders(action, context, state) -> (action, state)`: preserve baseline
  unit auction; filter market commitments by current cash, reserves, target deficit,
  stock and horizon. At most three acquisition attempts per type/day. Proposals are
  recorded separately from subsequent observed outcomes. Sales, labor and feed have
  priority over growth. Prices may move within market execution; stock/cash checks
  use observations and estimates, not a guarantee that an order executes.
- `situation_packet(context, state) -> list`: at most two situation-matched own
  advancing completed plan examples immediately before the live state. This packet
  is available to FLORA/Claude; the deterministic adapter does not replay example
  actions or treat positive local asset progress as demonstrated terminal profit.

Daily completion requires actual installed and crop targets plus zero uninstalled
livestock. The next day expires unmet targets and replans from actual stock. A
completed plan does not authorize unlimited same-day buying. Unit scheduling still
uses dispatch_balanced; installation target persistence is strategic, not a promise
that individual workers finish their travel/build jobs. FLORA owns that scheduling.
Terminal behavior uses the baseline return/drop/sell actions and prohibits new
acquisitions. ROWAN owns detailed event timing; the exposed horizon is a conservative
first-production feasibility bound, not an event simulator or crop valuation model.

Run from repository root:

```bash
python -B revenue/kaggriculture/cloud-compiled-context/test_controller.py
python -B revenue/kaggriculture/cloud-compiled-context/build.py
python -B revenue/kaggriculture/cloud-eval/evaluate.py --engine-dir /tmp/kag-engine --candidate revenue/kaggriculture/cloud-compiled-context/candidate.py --opponent dispatch_balanced=revenue/kaggriculture/cloud-composition/candidate.py --seeds 9300101 --output /tmp/context-pilot.json
```

The engine cache must contain the evaluator's exact pinned upstream source.
`candidate.py` defines `agent` last for the official last-callable loader. Module
memory persists only within a game process; no filesystem writes or network.

Owner-authored code is MIT OR CC-BY-4.0; full grants accompany this directory.
Copyright 2026 Bryce Xavier Muhlnickel / TokenJunkieLabs. Baseline authorship remains
Euler / ASTRA-WORK / ROWAN / SORREL / FLORA. No third-party code is relicensed.

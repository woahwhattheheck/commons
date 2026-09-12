# V5 bulk feeder / pocket routing

Additive research carrier for `ASTRA-V5-BULK-FEEDER-POCKET-ROUTING`.

## Source theorem

Pinned official engine blob `3c202c7ee921da239356789e266b694635103fc4` makes worker inventories persistent within a day and does **not** impose a pocket capacity. A shed-adjacent `PICKUP(product, n)` converts `n` with `int(...)`, requires a positive quantity, clamps the transfer to current shed stock, subtracts the transfer from the shed, and adds all transferred units to that worker inventory. `FEED` consumes one carried WHEAT; `FERTILIZE` consumes one carried FERTILIZER.

There is no ground cache: `DROP`/item `PLACE` deposit at the shed, and end-of-day auto-drop can still lose overflow when aggregate carried goods do not fit `shedCapacity`.

So the only useful theorem is **route-aware pocket preload**: if a worker already visits the shed for a first WHEAT/FERTILIZER pickup and later makes another same-day refill before a later consumer, the first pickup could request the later refill quantity too. That can save the later pickup callback and, when the refill path contains backtracking, potentially shorten the movement path. A production rewrite is legal only when live observed shed stock covers the preload and the resulting same-day/EOD stock ledger is safe.

## Stage 1: frozen-route census

`route_census.py` is deliberately diagnostic-only. It exact-pins current frozen Arlene vendor blob `bdb9cf58148a3c7961c085f4902759537decabf6`, decodes its authored routes, and searches each day/worker for consecutive WHEAT/FERTILIZER pickups.

A static witness is emitted only when:

- both pickups are in the same day and for the same product;
- a matching consumer (`FEED` or `FERTILIZE`) occurs after the first pickup and another after the refill;
- between those two consumers the worker performs only PASS, movement, and exactly that one matching refill;
- no HARVEST/CARE/COLLECT/BUILD/etc. is hidden inside the candidate segment.

For every witness the census reports the preload/refill/service turns, authored quantities, raw movement count, net displacement, Manhattan-direct movement count, backtracking count, and an **upper bound** on reclaimable callbacks: one refill slot plus movement backtracking.

That is not a legality or profit certificate. It is only a cheap engagement gate for whether current frozen continuations contain the mechanism at all.

Run from `cloud-execution-lab`:

```bash
python candidates/v5/research/bulk-feeder-pocket-routing/test_route_census.py
python -O candidates/v5/research/bulk-feeder-pocket-routing/test_route_census.py
python candidates/v5/research/bulk-feeder-pocket-routing/route_census.py
```

## Decision gate

- `NO_STATIC_WITNESS`: classify v1 COLD and stop. Do not build a runtime hook.
- `WITNESS`: rank by `saved_slots_upper`, then build stage 2 around the smallest real segment. The runtime experiment must verify current route/source identity, current worker action/position, observed shed stock sufficient for the extra preload, exact consumer sequence, no intervening conflicting inventory mutation, and aggregate EOD shed-cap safety. It must fail closed to canonical action on any mismatch.
- Only measured engagement plus matched economic gain can justify a production-hook request.

Production runtime, default/config, archive, Kaggle submission, scheduler, `frozen_selected`, exec-pace, town, CAREBANK, and animal-yield-cap lanes are intentionally untouched.

# V5 portable-inventory semantics

Status: **source-proven research theorem; no gameplay activation**.

Authoritative source: `reference/engine/kaggriculture.py` Git blob `3c202c7ee921da239356789e266b694635103fc4`.

## What the engine actually does

The original “ground storage / tile cache” hypothesis is false. `DROP` and `PICKUP` are not tile-storage operations. They operate on the private shed and are legal only while standing on one of the four shed-access tiles. Farm tiles never receive dropped products.

The adjacent mechanic is real and strategically relevant:

- Harvested / collected products live in the acting farmer or hand's private inventory.
- Those per-unit inventories are not charged against `shedCapacity` while they remain carried intraday.
- Market `SELL` consumes **shed stock only**; carried stock cannot be sold directly.
- Explicit unit `DROP` executes **before** the current market queue. It transfers only what fits and then removes the entire carried item entry, so overflow is destroyed.
- At end of day, the engine runs the market first and only then `_drop_inventories_to_shed`. That automatic deposit again discards overflow, then all hand inventories are reset.
- Therefore carry is an intraday capacity buffer, not cross-day storage.

## Frontier implication

There is a precise action-order opportunity that is safer and more useful than “ground caching”:

1. If a worker is carrying valuable product while the shed is full or nearly full, an explicit `DROP` before a same-callback `SELL` can destroy cargo that would have fit after the sale.
2. On the final turn of a day, keeping the cargo carried lets the market execute first; provably successful current `SELL`s can create real shed room before the engine's automatic end-of-day deposit.
3. Outside day-close, a capacity-aware route finalizer can sometimes delay `DROP` until after a prior market sale has freed room, at the cost of one unit action / route tempo.

This is **not** a standalone policy in this directory. Canonical `spatial_tempo.py` already owns carried-fertilizer state and an active worker-route finalizer owner is editing that surface. The correct integration is for that owner to consume this theorem rather than fork another producer.

### Required safety proof for any integration

A future carry/delay transform should fail closed unless it can prove all of the following from current public/private state and the final returned action:

- exact carried item and quantity,
- exact pre-market shed occupancy,
- no pre-market deposit that consumes the claimed room,
- executable current market prefix and bounded `SELL` quantity from stock already in the shed,
- any same-market `BUY_PRODUCT` / `BUY_ANIMAL` arrivals that consume room,
- day-close ordering when relying on automatic deposit,
- no assumption that carried stock itself can satisfy the current `SELL`,
- no credit for a sale that depends on the carried units being deposited first.

The reusable machine-readable receipt is `THEOREM.json`; `verify_portable_inventory_semantics.py` authenticates the pinned engine blob and the exact source-order invariants.
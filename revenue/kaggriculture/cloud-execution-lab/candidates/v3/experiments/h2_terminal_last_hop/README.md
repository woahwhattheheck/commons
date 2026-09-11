# H2 — terminal last-hop cargo rescue

Default-off V3.1 experiment on exact frozen base `508b342fc46fa91e3d7cdc3f0b7e44934a187c14`.

## Source theorem

Frozen R04 owns terminal liquidation at step 718. Its `liquidate(view)` emits `DROP` only for workers already beside the shed, then sells the projected shed. A worker entering step 718 one tile away with positive product cargo cannot move and liquidate on the same callback, so that cargo is stranded.

An older unpublished `h2_terminal_cargo` branch tried to solve the broader deadline-routing problem but could replace live `CARE`, `HARVEST`, and movement/service work during steps 696–717. This carrier intentionally does **not** inherit that behavior.

The H2 factor here owns only a one-callback seam at step 717:

- candidate worker has literal parent `PASS`;
- candidate holds positive product cargo;
- candidate is exactly one move from an unoccupied shed-adjacent cell;
- no other worker is moving;
- every other worker command is non-producing/storage-neutral, excluding `HARVEST` and `COLLECT_FERTILIZER` so the private-stock bound cannot grow after the census;
- parent market is SELL-only, excluding buys that could grow private stock;
- current shed stock + **all** carried product cargo fits the standard 100-unit shed;
- all observation/configuration/cargo/market scalar types and shapes are strict standard forms.

When those facts hold, H2 replaces exactly one lowest-index worker `PASS` with the existing R04 `_v219_walk()` one-hop movement. Step 718 remains the untouched parent liquidation. No market row, sale quantity, sale-window debt, price policy, route plan, worker service, or earlier callback is changed.

## Why capacity is part of the theorem

The official `DROP` behavior can lose excess cargo when shed capacity is exhausted. H2 therefore does not route cargo home merely because the geometry works. It requires the current shed plus every worker's carried product cargo to fit, and excludes same-turn private-stock-producing worker/market actions. This makes successful last-hop arrival safe for the unchanged step-718 DROP/liquidation path.

## Evidence boundary

This PR is a source/safety carrier, not an economics claim. Its first execution gate is an exact-interpreter activation/realization census on opponent-diverse games:

1. count step-717 eligible last-hop rescues;
2. verify the selected worker is beside the shed on step 718;
3. verify protected units enter the shed and are included in terminal liquidation;
4. record terminal own/rival scores and `Δown / Δrival / ΔM`;
5. apply the D3 externality gate, because extra terminal supply can affect a rival selling the same product.

**Zero activations closes H2.** Any realized regression or rival-benefit externality keeps it default-OFF. Do not broaden into WATER/HARVEST prioritization here; H1 owns terminal worker-priority changes.

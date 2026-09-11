# C5 — public WHEAT buy-signal rider (experiment only)

Status: **default-OFF / source-mechanics candidate / no economics or promotion claim**.

This experiment is a narrow implementation of Muse's C5 wheat-demand-rider idea on the frozen V3.1 base (`508b342fc46fa91e3d7cdc3f0b7e44934a187c14`). It does not add WHEAT supply, predict hidden rival orders, borrow a future sale, or touch animal/feed routing.

## Public attribution theorem

The official interpreter has one important hard-floor wrinkle: a successful SELL quoted above $1 increases public market inventory, but a successful SELL quoted at exactly $1 pays the seller **without** increasing market inventory. Therefore inventory transitions cannot prove rival `BUY - SELL` net demand when hidden floor-price rival sells may also occur.

What the public transition can prove is a conservative lower bound on **gross realized rival WHEAT BUY units**. Let visible sells mean successful SELL units that actually increment market inventory. Between callbacks:

```text
delta_market_wheat =
    own_visible_sell + rival_visible_sell
    - own_buy - rival_buy - town_consume
```

The candidate knows prior/current public WHEAT inventory, deterministic town consumption implied by the prior public step + unlocked shops, and its own prior **requested** WHEAT BUY quantity. Since successful own BUY cannot exceed that request and both visible-sell terms are non-negative:

```text
rival_buy >=
    previous_inventory - current_inventory - town_consume - own_buy_requested
```

A positive lower bound therefore proves at least that many realized rival `BUY_PRODUCT(WHEAT)` units. It intentionally makes **no** claim about hidden rival net demand after SELLs. Failed own buys and visible own/rival sells can only make the bound smaller. No rival private inventory or order list is read.

## Candidate transform

After a proven prior-step rival-BUY event, C5 considers the current parent action only when the public WHEAT price is above the $1 floor. It requires exactly one current executable WHEAT market row, and that row must already be a positive `SELL`.

The executable prefix is derived from runtime `maxMarketOrdersPerTurn` for exact non-bool integers, matching official integer clamping with `max(1, cap)`. Bool/float/string/`None` cap values fail closed rather than relying on the engine's coercion. If the executable prefix has a real free raw slot and there is no cash-spending executable order after the WHEAT sale, C5:

1. deep-copies the parent action;
2. replaces the original WHEAT SELL row with `[]`;
3. appends the exact unchanged WHEAT SELL row at a new executable trailing index.

Every other raw row stays at its exact original index and content. Farmer/hand actions and total WHEAT SELL quantity are unchanged. Later HIRE/BUY_* rows veto the move so the sale cannot have been funding them. A raw tail beyond the executable cap is never compacted or shifted.

All current transition evidence is validated/materialized **before** any relocation decision. Unknown current shops, malformed cadence/cap/market evidence, step gaps/rewinds, same-product ambiguity, full executable prefixes, floor price, and disabled mode preserve the exact parent action. Malformed current evidence also clears the stored per-player transition so it cannot authorize a later callback.

The economic hypothesis is only that repeated rival WHEAT buying may make a later within-callback WHEAT quote better than the parent's earlier quote. That is **not** established by source mechanics. A paired official-interpreter gate must report `Δown`, `Δrival`, and `Δmargin`; D3 rejects any apparent own gain purchased by a larger rival gain.

## Source/custody scope

The dedicated workflow binds:
- frozen V3.1 base `508b342fc46fa91e3d7cdc3f0b7e44934a187c14` as an ancestor;
- the exact four-path `508b -> HEAD` C5 allowlist;
- R04 blob `21c4f1db0298f8955b1f5ad366bd780a89cad206`;
- official interpreter blob `3c202c7ee921da239356789e266b694635103fc4`;
- exact event-head checkout and clean-tree source tests.

The focused suite now covers the original attribution/row-isolation contracts plus current-evidence-before-mutation killers, exact runtime-cap 1/3 behavior, 0/negative clamp-to-one parity, bool/float/string/`None` cap poison, and raw-tail preservation.

## Explicit non-claims

- No claim that rival WHEAT buying persists into the current callback.
- No claim about rival net WHEAT demand after hidden SELLs.
- No claim that a relocation will activate on the frozen official panel.
- No official-gate or promotion authority.
- No overlay/default/config/manifest/package/evaluator/opponent/provider/Kaggle mutation.
- This is distinct from E7: deterministic town consumption is subtracted from the attribution signal rather than treated as rival buying.
- This is distinct from C1 same-index cycling: no BUY/SELL round trip is introduced.

Next useful gate: exact ready-V3.1 parent vs C5 under the pinned official interpreter, frozen seeds `2611151001..1008` both candidate seats, then a representative tape-heavy/off-tape mixture. Require activation telemetry (`confirmed_rival_buy_transitions`, `relocations`, `moved_units`, row indices) and per-cell D3 economics.

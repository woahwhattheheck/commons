# C5 — public WHEAT demand rider (experiment only)

Status: **default-OFF / source-mechanics candidate / no economics or promotion claim**.

This experiment is a narrow implementation of Muse's C5 wheat-demand-rider idea on the frozen V3.1 base (`508b342fc46fa91e3d7cdc3f0b7e44934a187c14`). It does not add WHEAT supply, predict hidden rival orders, borrow a future sale, or touch animal/feed routing.

## Public attribution theorem

For the official interpreter, after one callback:

```text
delta_market_wheat = own_sell - own_buy + rival_sell - rival_buy - town_consume
```

The candidate knows the prior public WHEAT inventory, the current public inventory, the deterministic town consumption implied by the prior public step + unlocked shops, and its own prior **requested** WHEAT BUY quantity. Since successful own BUY cannot exceed that request and successful own SELL is non-negative:

```text
rival_buy - rival_sell >=
    previous_inventory - current_inventory - town_consume - own_buy_requested
```

A positive lower bound is therefore proof of realized rival net WHEAT demand. It is intentionally conservative: our own successful sells can hide rival demand, while failed own buys can only make the bound smaller. No rival private inventory or order list is read.

## Candidate transform

After a proven prior-step rival-demand event, C5 considers the current parent action only when the public WHEAT price is above the $1 floor. It requires exactly one current executable WHEAT market row, and that row must already be a positive `SELL`.

If the current executable prefix has room (<10 rows) and there is no cash-spending order after the WHEAT sale, C5:

1. deep-copies the parent action;
2. replaces the original WHEAT SELL row with `[]`;
3. appends the exact unchanged WHEAT SELL row at a new trailing index.

Every other row stays at its exact original index and content. Farmer/hand actions and total WHEAT SELL quantity are unchanged. Later HIRE/BUY_* rows veto the move so the sale cannot have been funding them. Same-product ambiguity, malformed evidence, step gaps/rewinds, unknown shops, full market prefixes, floor price, and disabled mode all preserve the exact parent action.

The economic hypothesis is only that repeated rival feed buying may make a later within-callback WHEAT quote better than the parent's earlier quote. That is **not** established by source mechanics. A paired official-interpreter gate must report `Δown`, `Δrival`, and `Δmargin`; D3 rejects any apparent own gain purchased by a larger rival gain.

## Explicit non-claims

- No claim that rival WHEAT demand persists into the current callback.
- No claim that a relocation will activate on the frozen official panel.
- No official-gate or promotion authority.
- No overlay/default/config/manifest/package/evaluator/opponent/provider/Kaggle mutation.
- This is distinct from E7: deterministic town consumption is subtracted from the attribution signal rather than treated as rival demand.
- This is distinct from C1 same-index cycling: no BUY/SELL round trip is introduced.

Next useful gate: exact ready-V3.1 parent vs C5 under the pinned official interpreter, frozen seeds `2611151001..1008` both candidate seats, first against the vendored representative opponent and then a tape-heavy/off-tape mixture. Require activation telemetry (`confirmed_demand_transitions`, `relocations`, `moved_units`, row indices) and per-cell D3 economics.

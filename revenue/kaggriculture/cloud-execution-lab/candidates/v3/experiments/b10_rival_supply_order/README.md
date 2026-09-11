# B10 — public rival-supply SELL ordering

Status: **default-OFF experiment / no economics or promotion claim**.

Exact base: `titan/v3.1-20260911@508b342fc46fa91e3d7cdc3f0b7e44934a187c14`.

B10 is deliberately narrower than a generic opponent model. Rival orders, shed stock, carried inventory, and policy identity are private, so the candidate does not try to infer them from visible tiles. Instead it uses only a conservative public lower bound on *already realized* rival net supply from the previous market transition.

## Public supply theorem

For each product between callbacks:

```text
delta_inventory = own_sell + rival_sell - own_buy - rival_buy - town_consume
```

The candidate knows prior/current public market inventory, deterministic town consumption implied by the prior public step + unlocked shops, and its own prior requested SELL quantities. Since successful own SELL cannot exceed requested SELL and successful own BUY is non-negative:

```text
rival_sell - rival_buy >=
    current_inventory - previous_inventory + town_consume - own_sell_requested
```

A positive lower bound proves realized rival net supply. The bound is conservative: our own BUY can hide rival supply, and failed or `$1`-floor own SELL requests only subtract too much because requested SELL upper-bounds inventory-increasing own supply.

## Transform

The exact ready-V3.1 R04 parent already sorts the leading SELL block by its native own-curve drop heuristic. B10 runs *after* that parent and only when at least one prior-step product has a positive public rival-supply lower bound.

Within the existing leading SELL block:

- WHEAT stays at its exact row index; C5 owns WHEAT-demand timing and feed-sensitive behavior.
- Every non-WHEAT SELL row and quantity is preserved exactly.
- Products with larger proven rival net-supply lower bounds move earlier among the non-WHEAT positions.
- Equal evidence keeps native R04 relative order via stable sorting.
- Any later `HIRE` / `BUY_*` row vetoes the transform, avoiding a change to sale-funded purchase execution.
- No row is added or deleted; non-leading rows, farmer/hand actions, and total product quantities are exact-parent.
- Step gaps/rewinds, malformed public evidence, unknown shops, custom market parameters, oversized market prefixes, and no-positive-evidence preserve the parent.

The causal hypothesis is that, if rival selling pressure persists into the current callback, clearing our already-planned sale earlier in the cross-player lockstep may improve our quote before additional same-product supply lands. **Persistence is not proved by the source theorem.** It is the gameplay hypothesis that must survive paired execution.

## Relationship to other lanes

- **Distinct from C5:** C5 detects prior rival net *WHEAT demand* and moves one current WHEAT SELL later. B10 detects prior rival net *supply* across products, never moves WHEAT, and only permutes existing leading non-WHEAT SELL rows.
- **Distinct from L3 / #12418:** #12418 uses public rival-supply evidence to decide whether to suppress late sale advancement. B10 leaves reservation/advancement untouched and changes only within-callback ordering of already-returned leading SELL rows.
- **Compatible with D3:** economics must report both own and rival deltas; any apparent own gain accompanied by a larger rival gain is a rejection.

## Required next gate

Source contracts are necessary, not sufficient. Run exact ready-V3.1 parent vs B10 under the pinned official interpreter on frozen seeds `2611151001..1008`, both candidate seats, with telemetry for positive-supply transitions and actual reorders. Report per-cell `Δown`, `Δrival`, `Δmargin` plus product/row-order activation. Then repeat on a representative tape-heavy/off-tape opponent mixture. Nonpositive margin or harmful externality kills the lane.

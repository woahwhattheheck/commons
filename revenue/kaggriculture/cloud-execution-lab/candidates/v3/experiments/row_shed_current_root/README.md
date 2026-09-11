# V3.1 S33 row-shed — current-root donor

Fleet claim: `TITAN-V31-8E3-ROW-SHED-CURRENT-ROOT-RECOMPOSE-20260911-01`.

## Authority boundary

This branch starts at literal shipped V3.1 root `8e3d92a286806f9f9525973ee7d359b629a11487` (#12537). It is an **additive experiment/evidence carrier only**: no `overlay/**`, `apply_v3.py`, package config/default, manifest/FILES, evaluator/opponent, provider, Kaggle, leaderboard, or submission state is changed.

The reason for an additive donor instead of a second live R04 writer is deliberate: #12541 owns the current-root L3 correctness rewrite on top of the #12535 immutable-base/build-custody line. Row-shed touches the same R04 seam, so this carrier makes the factor reviewable and executable without racing that writer. A later production consumer should recompose these exact semantics after #12541 (or its successor) and route the result through #12511.

## Mechanism

Shipped R04 `ROW_ORDER` stable-sorts only the contiguous leading SELL block by estimated price impact, but it currently scores each row using the tape's **requested** quantity. Several authored rows are availability dumps such as `SELL STRAWBERRY 1000`; physical shed stock can be only a handful of units.

S33 row-shed changes only the ranking quantity:

`q_eff = min(requested_sell_quantity, projected_shed[item])`

The emitted SELL row and quantity remain unchanged. Rows after the first non-SELL barrier remain unchanged. Equal scores remain stable. Explicit custom `marketParams` disables the transform exactly as incumbent `ROW_ORDER` does. Malformed projected-stock evidence fails closed to parent ordering.

`candidate.py` is an execution-ready wrapper over the current R04 module. It preserves the shipped tuple: horizon 8, opening 0, ROW_ORDER on, EVENING_FLUSH on, sale-fertilizer on, cattle-early on, H4 strawberry top-up on, rival-gated L3 on at step 648, and both B5 CARROT/JIT fertilizer lanes on. It disables native ROW_ORDER/EVENING_FLUSH only inside the candidate process, applies row-shed at the same market-order seam, then replays native evening flush. B5 can safely execute before the wrapper because B5 changes only PASS→FERTILIZE while R04 `projected_shed()` models only PICKUP/DROP/PLACE.

The `cattle_early` setting is deliberately overrideable for the separate #12540 one-key interaction gate; this carrier makes no cattle disposition.

## Evidence anchor

S33 field report in `#titan-kaggriculture`, parent message `1789122426.746929` (2026-09-11 06:27 EDT): official reference evaluator, 30 v25 shards × 32 seeds × both seats = 1,920 games per arm against 16 published agents. On the stale-a612 standalone module set, row-shed was better than the #12507 config in **1,912 / 1,920** games (6 worse, 2 same), added no opponent-level loss, and was reported **+421.1/game vs V3.0**.

Those scores are **donor evidence only** because canonical has advanced to 8e3 with B5 CARROT + JIT physically shipped. This branch does not launder the a612 result into current-root promotion authority. Current-root execution, then composition with the cattle-OFF decision if #12540 validates it, remains required before a default/package/submission change.

## Production consumption theorem

A later production consumer should make the minimum native edits:

1. add a default-OFF `r04_row_shed` package key / R04 install flag;
2. when `ROW_ORDER && r04_row_shed`, compute `projected_shed(action, FarmView(observation))` at the existing row-order call site;
3. pass that stock projection into `order_sells()` and use `min(requested, projected)` **only in the score calculation**;
4. preserve SELL rows/quantities, non-leading rows, H4, gated-L3, sale-fert, B5 CARROT, B5 JIT, and all other current-root bytes/flags;
5. keep row-shed orthogonal to cattle; compose whichever cattle arm survives #12540 above the same current root;
6. route the exact consumer head/blob/receipt into #12511 so the factor cannot remain an isolated side branch.

No merge/default/Kaggle authority is claimed by this donor.

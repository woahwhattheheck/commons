# S33 row-shed current-root donor

Fleet claim: `TITAN-V31-8E3-ROW-SHED-CURRENT-ROOT-DONOR-20260911-01`.

## Parent and purpose

This carrier is pinned directly to shipped V3.1 root `8e3d92a286806f9f9525973ee7d359b629a11487` (#12537), where B5 CARROT + JIT are already production bytes alongside H4 strawberry top-up, rival-gated L3, sale-fertilizer, horizon 8, and ROW_ORDER.

It is deliberately a **source donor**, not a competing R04 production branch. #12541 owns the in-flight fail-closed L3 rewrite of the same production file, so this branch freezes the row-shed delta as `repair.patch` plus focused contracts and does not mutate `overlay/r04_full_router.py` in Git history. That avoids a write collision while giving the fleet an exact durable object to consume above the then-current canonical.

## Mechanism

Current ROW_ORDER scores each leading SELL row from its requested quantity. A tape row can request far more than can actually leave the projected shed, causing the sort to price a fictional market impact and move that row ahead of executable sales.

The donor changes only that ranking input:

`effective_quantity = min(requested_quantity, projected_shed[item])`

`v3_agent()` already has the exact action and observation needed by `projected_shed()`. It computes the projection once for ROW_ORDER and passes it to `order_sells()`. The returned market rows retain their original quantities; only the ordering score is clamped. The non-SELL boundary and tail remain untouched. The two-argument `order_sells(market, inventory)` form keeps legacy requested-quantity behavior for source compatibility; production calls supply the shed projection.

## S33 predecessor field signal — not byte custody

Fleet coordination message `1789122426.746929` reported the same row-shed mechanism from the Gemini endgame lane on the official reference evaluator: 30 v25 shards × 32 seeds × both seats = 1,920 games per arm against 16 published agents. It reported 1,912/1,920 games better than the #12507 config, 6 worse, 2 same, no opponent-level loss, and +421.1/game versus V3.0.

Those numbers motivate priority but are **predecessor evidence only** here because the original Gemini source head/blob was not durably published. This donor re-expresses and source-tests the described mechanism against exact shipped 8e3 source; it does not launder the S33 score receipt onto a new blob.

## Focused contracts

`test_repair.py` AST-loads only the ROW_ORDER constants/functions from the ephemerally patched current router and proves:

- the V3 wrapper passes `projected_shed()` into ROW_ORDER;
- legacy two-argument scoring remains source-compatible;
- a 1000-unit requested WHEAT sale with only 10 sellable units no longer outranks a real 10-unit CARROT sale merely because of fictional quantity;
- zero sellable stock cannot outrank a realizable sale;
- the leading SELL block may reorder, but the non-SELL boundary/tail and row quantities remain unchanged.

The dedicated workflow pins exact 8e3 ancestry and router preimage, applies this patch ephemerally, runs the contracts, checks syntax/diff cleanliness, then restores the source tree.

## Convergence / landing contract

This PR is intentionally not merge authority for gameplay. Route it through #12511.

1. Let #12535 establish immutable build custody and #12541 finish the fail-closed L3 production head.
2. Re-apply this exact donor semantics to that then-current R04 (or a later canonical successor), resolving only mechanical context drift.
3. Prove B5 CARROT + JIT + H4 + fail-closed gated-L3 + sale-fertilizer remain enabled and unchanged; keep cattle/default decisions out of this source delta.
4. Regenerate deterministic FILES/MANIFEST/package receipts through the canonical builder and run the row-shed focused contracts in the materialized tree.
5. Bind score-facing economics on the current package. S33 is a strong diversity anchor, but the production consumer must report exact current-package paired results/custody rather than inheriting stale a612 authority.
6. Only one resulting current-canonical row-shed production consumer should survive; collapse/supersede sibling implementations and place the final cattle-off submission transform above the assembled gameplay stack.

No default, cattle, evaluator/opponent, package input, provider, Kaggle, leaderboard, or submission state is changed by this donor.

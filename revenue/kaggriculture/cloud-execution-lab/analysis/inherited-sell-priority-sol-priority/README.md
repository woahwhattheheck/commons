# TITAN V3 inherited SELL priority

Operation: `titan-v3-inherited-sell-priority-20260910-sol-priority-01`

This lane consumes the reconciled V1/V2 scheduler result without reviving the rejected target-domain reversion. The retained matched panel showed that target narrowing alone reduced mean candidate cash by 3.875, while the ordering/tie component contributed 8.375 mean candidate cash with six positive, zero negative, and twenty-six unchanged cells. This change isolates only the latter factor.

## Policy boundary

The predecessor creates `targets` by walking the fixed `PRODUCTS` tuple. The successor keeps exactly the same membership and quantities: every positive non-operating product currently in the shed remains a target. It changes only deterministic iteration priority:

1. keys already present in the scheduler's pending-intent ledger, preserving first-seen insertion order;
2. current inherited baseline SELL keys, preserving controller order and without moving overlapping pending keys; and
3. all remaining eligible products in the existing stable `PRODUCTS` order.

Both production paths consume one shared `ordered_targets()` helper: the direct `SellScheduler.act()` path and the selected-action `FrozenSelected.transform()` path. Optimizer mathematics, scenarios, horizon selection, funding certificates, feasibility, joint composition, market-slot preservation, emitters, controller routes, operating WHEAT/FERTILIZER ownership, and terminal settlement are unchanged.

## Exact predecessor custody

The materializer refuses source drift before applying the patch:

- `scheduler.py` Git blob `a483b24dd72b580d7d8811636b54d2d44f391575`;
- `frozen_selected.py` Git blob `fc7baf5c179818a55037f6a61d92984d81d1a21c`;
- `build_integrated.py` Git blob `05994d946885ff0fe2a2ce77439fd335174900aa`;
- `change.patch` SHA-256 `eada8856e6ca2d491562732b41a9e4b2e70429057b7211369f8c33b13f1b9cd3`; and
- `test_scheduler_priority.py` SHA-256 `fbfb264db89699fb66dbb98bca9adb54875b2f26e76cc3e2028681d8d45b14bc`.

`verify.py` checks exact predecessor identities before materialization and AST/text semantics afterward. It requires one helper definition, one call in each production path, removal of both fixed-order predecessor expressions, and inclusion of the new contract in the standalone archive's `checks/` inventory.

## Predecessor-killing contract

The integration test gives two products equal optimizer admission and score. Fixed `PRODUCTS` order selects the unrelated first product. The successor must instead select a previously pending product at the opposite end of `PRODUCTS`, while preserving the complete two-product stock domain, the inherited baseline SELL index, caller observations, and the caller action.

Additional contracts prove pending-before-baseline ordering, no key movement on overlap, stable append order for unseen stock, zero-pending first-seen priority, exact membership parity with the V2 all-shed target domain, input immutability, and shared use by both production paths.

## Hosted release boundary

The dedicated workflow applies the exact patch on GitHub-hosted Linux, runs the focused scheduler/selected-action suite, rebuilds the single canonical `exports/titan-current.tar.gz`, verifies the pointer and `SOURCE.json` closure, preserves the superseded archive, commits generated release bytes to the branch, and retains the machine receipt as a workflow artifact.

No game, provider, Kaggle upload, leaderboard submission, public-rank claim, or opponent-specific promotion is performed here. A paired control/candidate panel remains a separate integration decision.

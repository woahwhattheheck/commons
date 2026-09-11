# H4 — live-R04 strawberry same-row reservation candidate

Status: **default-off experiment; no score claim; not wired into shipped V3.1 defaults.**

## Why this exists

The live replay audit ranked strawberry throughput / sale sizing H4: the closest loss to
Hello San Francisco flipped by $29 after the rival sold 17 STRAWBERRY at step 701, and the
fleet measured weak strawberry value capture in the close-game set.  Riot's earlier commons
B9 (`riot/v3-strawberry @ 3984f016b`, local-only at handoff) reconciled future strawberry sale
commitments against discard-aware fillable quantity and reassigned useful quantity into a
current sale row.

That earlier implementation cannot be transplanted mechanically into live V3.1: it targeted
`frozen_selected.materialize_sales`, while live R04 bypasses that controller and delegates to
`overlay/r04_full_router.py`.

Live R04 already has E184 `reserve_sales()`, which advances known future sales into the current
turn and records per-due-step debt.  But E184 deliberately blocks an item whenever the current
market already contains a SELL for that item.  Therefore an undersized current STRAWBERRY SELL
prevents the sale window from reserving additional already-planned strawberry units even when
current projected shed stock can fill them.

`experiments/h4_strawberry/r04_h4_strawberry.py` closes only that live seam.

## Packaging boundary

H4 is intentionally kept under `experiments/` while it is standalone/default-off.  V3's
`build_v3.py` packages and hashes every file under `overlay/`; placing experimental code or
checks there would change package inputs and require regenerated `FILES.json` and
`V3-MANIFEST.json` even though H4 is not wired into the shipped policy.  The H4 CI therefore
runs the exact source baseline, the focused experiment checks, and `build_v3.py --check`.
Promotion into the live route must be an explicit integration step that wires the feature and
regenerates deterministic package manifests together.

## Contract

When explicitly enabled, and only from E184's normal `ADVANCE_START` onward:

1. Require exactly one current `SELL STRAWBERRY` row.
2. Reuse E184's conservative blockers: price < 2, same-item BUY_PRODUCT, current/queued/future
   same-item PICKUP, future same-item BUY_PRODUCT, animal-PLACE shed uncertainty, and the next
   72-step route boundary.
3. Compute current projected shed stock with R04's existing `projected_shed()`.
4. Treat `projected STRAWBERRY - current SELL quantity` as the only available top-up stock.
5. Scan only the existing E184 horizon for future tape `SELL STRAWBERRY` quantities, subtracting
   already-recorded `sale_window_debts`.
6. Increase the existing current SELL by at most that stock-backed planned quantity.
7. Record the moved quantities into the same per-due-step debt map E184 already subtracts later.
8. Never add a market row; a full 10-row market is therefore not a blocker.

No future sale => no top-up.  No extra current stock => no top-up.  Multiple current strawberry
rows => fail closed.  Flag off => exact action-object identity at the transform boundary.

## Composition order

The experimental `h4_agent()` preserves the live V3.1 order:

`POLICY_AGENT -> H4 strawberry top-up -> ROW_ORDER -> EVENING_FLUSH -> OPEN_ROUNDTRIP`

This matters because ROW_ORDER should see the final strawberry quantity, while EVENING_FLUSH
must residualize against the already-enlarged strawberry sale rather than emit a duplicate.

## Required gate before integration

Do **not** enable or merge into a submission from unit tests alone.  Run paired official
evaluator cells on identical seeds/seats/opponents with V3.1 vs V3.1+H4 and judge
`ΔM = Δown - Δrival`.

Trace at least:

- H4 proposed / admitted / filled strawberry quantity and due-step debt;
- strawberry shed stock immediately before and after the sale;
- strawberry harvest/deposit/discard units and value;
- current and future strawberry SELL requested vs actually filled;
- strawberry price path / realized VWAP;
- interaction with ROW_ORDER and EVENING_FLUSH;
- total own cash, rival cash, margin, W/T/L, seat strata and per-cell negatives;
- deadline/fidelity failures.

Early-kill if the candidate creates a same-item BUY↔SELL churn, consumes stock needed by a
PICKUP, duplicates an evening-flush sale, increases strawberry discard, increases zero-fill
strawberry quantity, or improves own receipts while paired competitive margin worsens.

## Source-custody boundary

This module is a source-grounded live-R04 equivalent derived from the released B9 contract; it
is **not** a claim to reproduce Riot's unpublished local `3984f016b` bytes.  Exact B9 bytes or
diff should still be published if available so the two implementations can be compared before
promotion.

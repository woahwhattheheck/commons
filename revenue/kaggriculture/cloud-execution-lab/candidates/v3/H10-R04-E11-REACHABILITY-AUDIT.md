# H10 — R04 / E11 reachability audit

Status: **NO FINAL-OUTPUT PORT**. This is a negative semantic-audit result, not a gameplay candidate. No default, package, config, or Kaggle submission change.

## Finding

The V3 package ships `overlay/e11_rival_sell.py`, but E11's safe canonical seam is not equivalent to H7/H9's final-action experiment seam.

`apply_v3.py` explicitly places E11 inside the canonical seller **before pending accounting** and passes an exact future-absorption callback. R04 is a whole-route delegate, so that canonical seller is never constructed.

R04/E184 owns its own sale timing state. Its outer sale-window layer calls `reserve_sales(...)` before returning the final action and records `state.sale_window_debts` for advanced quantities. The V3 row-order / evening-flush wrapper is later still. There is no E11 hook inside that debt-ownership boundary, and R04 source exposes no exact future-absorption callback to a final-output wrapper.

Therefore the tempting implementation — `final_r04_action -> apply_e11(...)` — is **semantically unsafe**.

## Exact predecessor

1. E184 advances 2 MILK and records a future debt of 2 MILK for the corresponding planned sale.
2. The final R04 action contains `SELL MILK 2`.
3. Public MILK price has dropped enough for E11 and exact future absorption would make deferral eligible.
4. A naive final-output E11 wrapper replaces that SELL row with `[]`.
5. R04's already-recorded `sale_window_debts` remains unchanged because `apply_e11` has no state/debt unwind interface.
6. At the future due step, R04 subtracts those 2 units from the planned sale even though the advanced sale was never executed.

That is not merely lost optimization value; it violates R04's sale-debt accounting contract and can suppress inventory liquidation twice.

`experiments/test_h10_e11_no_final_port.py` freezes this predecessor. A second test proves E11 correctly fails closed when an exact absorption callback is absent; inventing a heuristic absorption function is outside H10 and would weaken the ARGUS safety repair E11 was shipped with.

## Safe paths if E11 is revisited

Only two directions are admissible:

1. **Internal R04 seam:** insert an E11-equivalent decision *before* `reserve_sales` commits debt, with an exact official absorption callback available at that point; then prove reservation/debt behavior with predecessor tests.
2. **Debt-aware transaction:** redesign the R04 sale-window layer so SELL deferral and debt reservation are one atomic operation with explicit unwind semantics. This is a new composed policy, not a wrapper port, and needs its own ownership + paired economics gate.

Do **not** wire E11 after final R04 output, do not treat `e11_rival_sell=True` as reachable under R04 today, and do not substitute estimated absorption for the exact callback.

## Why this advances V3.1

H7 and H9 demonstrated that whole-route R04 bypasses older V3 hooks. H10 closes the obvious third feature without creating a hidden regression: O01/E20 are testable as evaluator wrappers (with their own caveats), but E11's state ownership makes the same pattern invalid. This prevents the fleet from spending official-evaluator budget on a structurally broken port and identifies the precise internal seam required for any future E11 composition work.

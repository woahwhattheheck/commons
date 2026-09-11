# B8 — additive budget guard (experiment only)

B8 is a default-off V3.1 factor built on frozen base `508b342fc46fa91e3d7cdc3f0b7e44934a187c14`.
It does **not** change `overlay/`, `TITAN-CONFIG.json`, the builder, package bytes, evaluator semantics, or a Kaggle submission.

## Source seam

R04 V219 and V233 already price their current additive transaction and apply fixed cash floors (`3000` for V219; `3000` initial / `1000` recurring for V233). Their request functions do not otherwise reserve later same-day native tape purchases.

B8 does not reimplement those request functions. It computes only an exact fixed-cost reserve from later same-day **native** tape rows and temporarily subtracts that reserve from the money visible to the existing V219/V233 budget test. The parent functions continue to own eligibility, capacity, order cap, hire accounting, state mutation, row construction, and every market/farm action.

The reserve includes only fixed-price `BUY_ANIMAL` and `BUY_SEED` rows. `BUY_LAND` is deliberately treated as incomplete because the official engine prices successive extra quadrants differently (`$1000/$2000/$4000`); a context-free future row cannot certify which price applies. Future `HIRE` and `BUY_PRODUCT` are likewise dynamic. Any such row, unknown opcode, missing/non-list market, malformed non-empty row, wrong arity, or poisoned item/quantity makes the guard fail open to exact parent behavior. A well-formed `SELL` contributes zero reserve and is never assumed as financing.

Official engine farm money is float-backed, so B8 accepts only nonnegative finite `int`/`float` money values while rejecting bool, strings, NaN and infinities. This type gate exists only to decide whether the reserve proof may run; it does not normalize or rewrite parent money.

The implementation performs a state-isolated shadow call only to determine whether the parent would have invested; parent telemetry is restored before the sole authoritative call. This makes activation telemetry causal rather than counting callbacks where the parent was already a no-op.

## Structural census

`census.py` scans the exact frozen 13×719 tape bank at every callback hour where committed V219/V233 can request additive spend. It uses the same fail-open parser as runtime, so any suffix containing state/market-dependent future purchases is incomplete. The dedicated workflow fails if the frozen policy has zero nonzero exact-reserve windows.

That is a **reachability-only** gate. A positive structural census does not prove runtime eligibility, activation, protected-purchase realization, or economics.

## Required evidence

This PR is a source-safe experiment carrier, not a promotion claim. Before any default/package/Kaggle mutation:

1. Exact-head focused contracts, frozen R04/tape custody, and the structural reachability census must pass.
2. Run a runtime activation census. Zero or negligible activations kills the lane cheaply.
3. For every activation, report layer, step, reserve, and real money, then verify the protected later native purchase actually executes rather than merely being affordable.
4. Paired official-interpreter evaluation must report `Δown`, `Δrival`, and `Δmargin` across opponent-diverse cells. Positive own score purchased by larger rival gain fails D3.
5. Any regression in parent action/state when B8 is OFF is a hard reject.

The factor is intentionally conservative: dynamic future costs are not guessed, malformed/incomplete tape evidence cannot create a reserve, and no hidden rival inventory/orders or future market quote is inferred.

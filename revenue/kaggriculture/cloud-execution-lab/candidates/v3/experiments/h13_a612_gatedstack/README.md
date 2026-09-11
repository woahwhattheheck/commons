# H13 on shipped V3.1 a612

Status: evidence-only interaction gate. No runtime/default/package-source/Kaggle mutation.

Exact authority for this experiment is the shipped V3.1 root `a6120d0ea1bdb75eb0da2239220efce551f624a6` from merged #12494. That package ships H4 STRAWBERRY top-up and rival-gated L3/no-late-sale-advance with `r04_sale_horizon=8`.

## Why rerun H13 now

Earlier frozen evidence was sharply regime-sensitive:

- with exact L3 held constant, horizon 10 beat horizon 8 on frozen seeds `2611151001..2611151008` x both seats: 16/16 positive, mean head-to-head margin `+1677.25`;
- unconditional H10 was independently negative on Arlene/starter probes and was rejected for default promotion.

The shipped #12494 stack changes the question again because L3 is now rival-gated and H4 is production-active. Therefore this gate does **not** ask whether horizon 10 should be enabled globally. It asks whether the 8->10 horizon factor remains positive on the exact shipped stack in both a tape-like exact-self regime and a policy-diverse Arlene regime.

## Isolation theorem

`run_current_stack.py` materializes the current score-facing submission twice from the exact checkout and canonical archive. It requires the current deterministic base package SHA-256 to match the shipped `V3-MANIFEST.json`, then builds:

- control: exact shipped submission with horizon 8;
- candidate: the same submission with horizon 10.

The two archives must have identical member sets and differ byte-for-byte in **only** `TITAN-CONFIG.json`. Recursive exact-type comparison requires the configs to differ only at strict integer `r04_sale_horizon: 8 -> 10`; JSON `bool`/`int` lookalikes cannot false-green. The following shipped score-facing keys are pinned in both arms: R04 enabled, H4 top-up enabled, rival-gated L3 enabled at step 648, sale-fertilizer enabled, cattle-early enabled, row ordering and evening flush enabled, opening roundtrip 0.

Vendored Arlene source and the official interpreter/evaluator are pinned. The runner leaves the checkout unchanged and writes only raw reports plus an evidence receipt outside the repository.

## Frozen panel

Seeds: `2611151001..2611151008`, both candidate seats.

Each horizon arm is evaluated against:

1. exact horizon-8 shipped self (`h8_self`), which is tape-like and also supplies an exact h8-vs-h8 tie/seat-mapping control;
2. vendored Arlene, a policy-diverse public opponent.

The evaluator does not expose the router's private `rival_on_tape()` classifier boolean. Therefore these are described as **regimes**, not asserted per-game gate states. The receipt reports paired `delta_own`, `delta_rival`, and `delta_margin` for every cell, plus seat-conditioned summaries.

## Decision rule

- Both regime mean deltas > 0: evidence may widen to the recorded 41-game replay set. This is still not default/promotion authority.
- Opposite mean signs: `HOLD` / selector or classifier work; do not flip horizon globally.
- Otherwise: H10 is not positive across the current shipped stack; stop promotion work.

A technically successful workflow with a negative economics disposition is a valid result and must remain green. Economics decides disposition; CI proves custody and execution.

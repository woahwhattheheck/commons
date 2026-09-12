# FLOORDRAIN current-native census

Status: **COLD on the authenticated b567 current-native panel; mechanism retained research-only / default OFF.**

This receipt closes the execution-only follow-through for the existing `floor_capacity_relief.py` helper. It does not build or wire a second seller/controller. The runner executes the authenticated current-native agent against itself, observes **both seats after the real UNIT phase and immediately before MARKET on EOD callbacks**, and projects the official EOD inventory-to-shed drop from the resulting private state. The already-merged FLOORDRAIN helper is then evaluated without changing any action.

## Exact tested result

Panel seeds: `17, 101, 6607, 2026091201, 2026091207, 2026091213, 2026091219, 9922999`, both seats (16 seat-cells).

- 8/8 seed games completed / 16 seat-cells observed.
- Official-interpreter observer control on seed 17 is trace- and score-identical to the unmodified evaluator.
- 10/16 seat-cells reached projected EOD overflow; 16 overflow callbacks total.
- Baseline projected discarded cargo: **88 units** total: WHEAT 42, CARROT 24, STRAWBERRY 20, FERTILIZER 2.
- **0/16 overflow callbacks had any currently held shed product quoted at the official `$1` floor.**
- Therefore FLOORDRAIN admissions = **0 callbacks / 0 units**. No ON policy arm was executed because a correctly guarded ON arm has nothing to change.
- Every observed overflow callback already carried authored market work (`rows_used` 1 on 14 callbacks, 2 on 2 callbacks), which further argues that future composition must go through the existing market-row owner rather than append a new seller blindly.

Disposition is `COLD_CURRENT_NATIVE_TESTED_PANEL`, not a mechanism kill. The synthetic engine theorem remains valid: when projected overflow coexists with unprotected `$1` shed cargo, floor sale can free capacity without increasing public market inventory. This current runtime simply does not naturally reach that conjunction on the tested panel.

## Custody and safety boundary

The runner pins the existing helper Git blob `f162562d445b6f6a864ba43c884b7e96dcfbbd41`, official engine blob `3c202c7ee921da239356789e266b694635103fc4`, and authenticated current-native `main.py` SHA256 `c4c22d0f2b1071cadf6a9f74effccc8cb20ea9f4d10ca1cf9f1fe57351709dc1`. It uses runtime artifact `10180428228` / `titan-current.tar.gz` SHA256 `b567942e4fb4e0571ebf9f8eaaf143d4a9156df3289f09a98db37823ef4d68d9`.

WHEAT and FERTILIZER shed stock are fully protected in the helper admission probe so this execution experiment cannot steal feed/service inventory. Shed shadow values use official base prices; incoming cargo values use the current public quote. Unknown values remain fail-closed in the existing helper.

No runtime, config, default, controller, archive, composition graph, or Kaggle submission is changed here. `CARRYCOMPOSE` keeps current-ABI integration ownership. Re-open field economics only if a newer canonical current postimage naturally produces projected overflow **and** an unprotected `$1` shed product; at that point require paired both-seat output-changing economics and exact reserve/market-delta checks before any activation proposal.

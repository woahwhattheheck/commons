# TITAN V4 scheduler calendar custody

Status: **SOURCE-BOUND CANDIDATE / DEFAULT-OFF / NO PRODUCTION MUTATION**

This is a second-stage source repair in the existing `scheduler-prefix` authority. It consumes the exact scratch output of `materialize_scheduler_prefix.py`; it is not a sibling scheduler/controller and does not edit `scheduler.py` in place.

## Defect

Current `SellScheduler` accepted `config`, but five scheduler-calendar decisions were still hard-coded to 24 callbacks:

- `cash_reserve()` reset `hires_today` when `t % 24 == 0`;
- `receipt_profile()` passed `t // 24, 24` to future `_apply_unit_action()` calls;
- `receipt_profile()` performed represented EOD drop/termination when `t % 24 == 23`;
- `act()` clipped its planning horizon to `(now // 24 + 1) * 24 - 1`;
- the naive `act()` path treated only `now % 24 == 23` as EOD.

The official interpreter derives `turns_per_day` from configuration and uses it for day indexing, unit dispatch, and `(step + 1) % turns_per_day == 0` EOD. The standard configuration remains 24, so this closure is behavior-preserving there. On nonstandard calendars the predecessor can reset Fibonacci HIRE spend on the wrong callback, simulate unit actions under the wrong day index, drop represented inventories at the wrong boundary, and plan across a real EOD. The closure also rejects malformed calendar evidence instead of authenticating it through Python coercion.

## Bound composition

1. raw scheduler Git blob `a483b24dd72b580d7d8811636b54d2d44f391575`;
2. canonical prefix materializer Git blob `f36e9120ea07c861a7eca5821a5306c6dbfa4613`;
3. exact prefix scratch output Git blob `1da9934ec45f485a16244bcbc78af26d9109b97e`;
4. official engine Git blob `3c202c7ee921da239356789e266b694635103fc4`;
5. then `materialize_scheduler_calendar.py` applies only the calendar closure.

The new helper accepts only a positive plain `int` `turnsPerDay` (default 24 when the key is absent). `bool`, float, string, null, containers, zero, and negative values fail closed. `SellScheduler.act()` binds that value before any represented unit projection; the two independently callable projection helpers bind it again at their own source boundaries.

## Validation receipt

Exact authored candidate against the bound prefix/engine bytes:

- focused suite: **15/15 PASS** normal;
- focused suite: **15/15 PASS** under `python -O`;
- `py_compile`: **PASS**;
- exact CLI scratch materialization: **PASS**;
- candidate scheduler Git blob: `b435de06c291186ae5895e2db7667fb1fc1c149f`.

The focused contracts cover the exact raw→prefix→calendar chain, engine source anchors, canonical 24 parity, 12-turn predecessor killers for HIRE reset, future unit-day arguments, represented EOD, horizon clipping and naive EOD handling, plus type poison, source/engine drift, double apply, ambiguous/missing anchors and exclusive-output custody.

## Boundaries

No runtime/default/config/COMPOSITION/INTEGRATION/archive/Kaggle change. No gameplay or economics promotion claim. The existing executable-prefix lane retains market-prefix authority, and the separately claimed represented physical-transition lane retains purchase/HIRE execution authority. This artifact owns only calendar semantics across `SellScheduler.cash_reserve()`, `receipt_profile()` and `act()` after canonical executable-prefix composition.

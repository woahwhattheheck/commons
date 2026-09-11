# A1 — kill V219 late-TOMATO investment on shipped `a612`

This directory is an **evidence-only ablation**. It is a direct child of merged
canonical `a6120d0ea1bdb75eb0da2239220efce551f624a6` and changes no production
overlay, config/default, package input/manifest/FILES receipt, evaluator,
opponent, submission, or Kaggle artifact.

## Replay hypothesis

Fleet replay forensics on 31 live episodes reported that V219's day-18 TOMATO
program produced no realized TOMATO shed output while ten planted tomatoes
vanished unsold. That is a hypothesis to test on the current shipped stack, not
an inherited score claim.

## Source boundary

V219 is unusually clean to ablate. At step 432 its own `_v219_qualifies()`
requires all of the following before committing:

- the SE quadrant is still locked/spare;
- no existing TOMATO seed, shed stock, or planted TOMATO exists;
- the native day18..29 tape has no BUY_LAND or PLANT TOMATO obligation;
- liquidity/shop/price predicates pass.

Only then V219 buys its own land and ten TOMATO seeds, requests additional
worker indices, and later overwrites only those newly confirmed V219 workers
with its plant/water/fertilize/harvest/return commands. It separately appends a
TOMATO sale only when its projected shed contains TOMATO.

`candidate.py` therefore does not delete rows after the fact. It calls the exact
shipped outer R04/H4/L3 chain while temporarily replacing only
`_v219_qualifies()` with an always-false predicate; the original predicate is
restored in `finally`. This is a full V219 investment ablation with every parent
and later layer preserved.

## Current-stack gate

Dedicated CI runs the pinned official interpreter on seeds
`2611151001..2611151004`, both seats, in two regimes:

1. exact `a612` self-play;
2. vendored Arlene.

For each regime it compares exact `a612` control against the V219 ablation and
reports full trace activation plus paired `Δown`, `Δrival`, and `ΔM`.

Fail-closed disposition:

- zero trace deltas → reject as unreachable on the tested current stack;
- any negative `ΔM` cell → hold;
- a nonpositive mean `ΔM` in either regime → hold;
- positive means in both regimes with no negative cells → promising only.

A promising result authorizes only a reviewed **default-OFF production seam**
plus materialized OFF-identity/ON-reachability and wider D3 economics. It does
not authorize default-true, merge, submission, or Kaggle upload.

# A6 — V226 dynamic WHEAT top-up ablation on shipped `a612`

This directory is an **evidence-only ablation**. It is a direct child of merged
canonical `a6120d0ea1bdb75eb0da2239220efce551f624a6` and changes no production
overlay, config/default, package input/manifest/FILES receipt, evaluator,
opponent, submission, or Kaggle artifact.

## Replay hypothesis

Fleet forensics over 31 live episodes reported roughly 156 purchased WHEAT
units while the same agent sold roughly 622 homegrown WHEAT. That makes wheat
purchase timing a high-value audit target, but later surplus does not prove an
earlier feed purchase was avoidable.

## Engine timing matters

The pinned interpreter applies farmer/hand actions **before** market orders on
each step. A `BUY_PRODUCT WHEAT` at step `t` therefore lands in the shed only
after step-`t` worker actions, but it is available to a shed-adjacent
`PICKUP WHEAT` at `t+1`. Harvested wheat carried by a worker is not shed stock
until a later `DROP` or end-of-day inventory deposit.

That is exactly what V226 is designed around. After the inherited action is
built, `_v226_topup()` looks at an already-scheduled next-step WHEAT pickup,
projects current shed stock, and appends a bounded `BUY_PRODUCT WHEAT` shortage
when the pickup would otherwise exceed projected stock. It caps the shortage at
4 per order and 8 units/day and refuses to stack with other purchases or WHEAT
market rows.

So the safe first question is **not** “delete all wheat buying.” It is whether
V226's dynamic bridging purchases are net-positive on the current shipped
stack.

## Exact ablation boundary

`candidate.py` temporarily replaces only `_v226_topup()` with an identity
function while the exact shipped outer R04/H4/L3 agent runs, restoring the
original helper in `finally`.

Unchanged and still live:

- native tape WHEAT purchases;
- V233 initial/daily sheep-feed WHEAT purchases;
- V234 sheep-rescue WHEAT purchases;
- all worker commands and pickups;
- cattle behavior, H4 strawberry top-up, rival-gated L3, market row order, and
  every later wrapper.

This isolates the actual V226 timing mechanism instead of conflating all WHEAT
purchases.

## Current-stack gate

Dedicated CI runs the pinned official interpreter on seeds
`2611151001..2611151004`, both seats, in exact-`a612` self-play and vendored
Arlene. It compares exact control against V226-ablation and reports full-trace
activation plus paired `Δown`, `Δrival`, and `ΔM`.

Fail-closed disposition:

- zero trace deltas → V226 did not activate in the screen; reject/no evidence;
- any negative `ΔM` cell → hold;
- nonpositive mean `ΔM` in either regime → hold;
- positive means in both regimes with no negative cells → promising only.

A promising result supports only the next reviewed V226 reduction/production
gate. It does **not** prove all observed wheat purchases are waste, and it does
not authorize default-true, merge, submission, or Kaggle upload.

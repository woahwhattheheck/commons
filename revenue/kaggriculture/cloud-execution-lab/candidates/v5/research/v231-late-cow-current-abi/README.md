# V231 late COW acquisition — current ABI research carrier

This carrier recovers one score-shipped V3.1 semantic that current V5 is missing:
the **late** V231 livestock substitution. It remains a selected-action transform only;
it does not call or replace the current producer/controller.

## Why this exists

The current S2 COW→SHEEP experiment is cold because current V5 emits zero
`BUY_ANIMAL COW` orders for S2 to rewrite. Submitted V3.1 still contained V231.
The exact submitted router proves two distinct windows:

- `_V231_EARLY` controls only steps 190–215. Submitted V3.1 shipped
  `cattle_early=false`, so this carrier deliberately does **not** implement that window.
- the V231 `_late` window at steps 216–227 is independent of `_V231_EARLY`.
  When its milk-shop/price/ownership gates hold, it rewrites exactly one existing
  `BUY_ANIMAL SHEEP` order (quantity 1–2) to COW, then owns the corresponding
  SHEEP→COW pickup/place continuation and only credits extra harvested milk into an
  already-existing MILK sale row.

That distinction prevents accidentally reviving the held early-cattle feature while
restoring the upstream opportunity that the current S2 gate explicitly reported missing.

## Submitted authority

- V3.1 source commit: `a90d888f03987ef0b35cfd20ec3519c6144db08a`
- `overlay/r04_full_router.py` Git blob:
  `a3e2fe87c717d128e43c9b65bae2265f40d1d76d`
- `overlay/r04_full_router.py` SHA-256 recorded by submitted `FILES.json`:
  `41ea55c5f20c43cd58c5099fbadb212de62ec95a95dfc2e6e1e19c3d4d55b39a`
- submitted V3.1 archive SHA-256:
  `5db3921f85efbc7596e5a1e7e198fc5f4644ceea43d8e8323c74ded7b4ba4361`

The historical source is authority for semantics, not current promotion evidence.

## Current surface

The carrier intentionally has two layers with one public current-ABI entry point:

- `v231_late_current.V231LateCurrentABI` is the donor-semantic core. It preserves the
  historical whole-router `step <= last` reset so the recovered late decision/lifecycle
  theorem can be compared directly to submitted V3.1. Its boundary validation is
  fail-closed, including malformed selected-hand shapes.
- `v231_late_current_safe.V231LateCurrentABISafe` is the **public current selected-action
  surface**. It owns same-step retry custody only; it does not alter the donor decision
  theorem and does not add a producer/controller call.

`enabled=False` is detached identity. `enabled=True` applies only the late V231 theorem.
The carrier is research-only: there is no runtime feature, config/default flip, archive
rebuild, release pointer change, or Kaggle mutation here.

Current callbacks may retry the same public step. The safe envelope captures the exact
pre-step V231 candidate state once. Every valid same-step retry is recomputed from that
same preimage, so an identical retry is action/state idempotent while changed valid
evidence replaces the abandoned attempt rather than inheriting its post-state. A malformed
retry is detached identity and cannot mutate transaction or candidate state. A true rewind
starts a fresh epoch.

## Focused contracts

The combined suites prove:

- exact submitted authority pins;
- OFF identity and strict-bool activation;
- steps 190–215 remain OFF even under otherwise qualifying conditions;
- steps 216–227 rewrite only the exact bounded SHEEP purchase under the submitted late
  milk-shop / no-YARN / MILK>=WOOL / herd / cargo / sole-animal-order gates;
- confirmed purchased COW stock owns the corresponding PICKUP/PLACE continuation;
- placement confirmation binds the owned site/day;
- harvested milk credit can enlarge an existing MILK sell row but never invent one;
- malformed current envelope/cardinality/scalar-hands drift fails closed;
- identical purchase and HARVEST retries are action/state idempotent on the public safe
  surface;
- changed same-step selected evidence retires an abandoned purchase before the next
  callback;
- changed HARVEST evidence restores pre-step authority instead of retaining first-attempt
  milk credit/sale effects;
- malformed same-step retry leaves both candidate state and retry transaction unchanged;
- rewind resets the V231 epoch.

## Local gate

From this directory:

```bash
python -m py_compile \
  v231_late_current.py v231_late_current_safe.py \
  test_v231_late_current.py test_v231_late_retry_safe.py
python -B -m unittest -v test_v231_late_current.py test_v231_late_retry_safe.py
python -O -B -m unittest -v test_v231_late_current.py test_v231_late_retry_safe.py
```

Current combined local receipt on these authored bytes: **19/19 normal, 19/19 `-O`,
compile PASS**. The dedicated exact-head Python 3.11/3.12 workflow runs the same four
files and also requires a clean source tree after execution.

Promotion requires a fresh current-V5 matched screen. First measure OFF vs
`V231LateCurrentABISafe(enabled=True)`. If it engages and survives economics, test the
composed V231-late → existing gated S2 path on the same opponent/seed/seat panel. No
default activation is justified by this source carrier alone.

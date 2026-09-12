# V231 late COW acquisition — current ABI research carrier

This carrier recovers the score-shipped V3.1 **late** livestock substitution without reviving `cattle_early`, replacing the producer/controller, or changing a production default.

## Submitted authority

- V3.1 source commit: `a90d888f03987ef0b35cfd20ec3519c6144db08a`
- `overlay/r04_full_router.py` Git blob: `a3e2fe87c717d128e43c9b65bae2265f40d1d76d`
- router SHA-256 from submitted `FILES.json`: `41ea55c5f20c43cd58c5099fbadb212de62ec95a95dfc2e6e1e19c3d4d55b39a`
- submitted archive SHA-256: `5db3921f85efbc7596e5a1e7e198fc5f4644ceea43d8e8323c74ded7b4ba4361`

Submitted source separates `_V231_EARLY` (steps 190–215, gated by `cattle_early=false` in the winner) from the independent late path at steps 216–227. Only that late theorem is recovered here: under the submitted milk-shop/price/herd/cargo/sole-animal-order gates, an existing bounded `BUY_ANIMAL SHEEP` may become COW; confirmed stock owns its matching PICKUP/PLACE continuation; extra harvested milk can enlarge an existing MILK SELL but never invent one.

## One public current surface

The implementation has two internal layers but one public selected-action entry point:

- `v231_late_current.V231LateCurrentABI` is the source-faithful donor core. It deliberately retains the historical whole-router `step <= last` reset.
- `v231_late_current_safe.V231LateCurrentABISafe` is the **public current ABI**. It owns retry custody only and never calls a producer/controller.

The safe envelope captures one immutable pre-step candidate snapshot per `(player, step)`. Exact valid retries return the recorded action/post-state without re-entering the donor core. Changed valid evidence for the same public callback recomputes from that same pre-step authority, retiring the abandoned attempt. Full envelope validation happens before transaction mutation, so a malformed same-step retry is detached identity and cannot rewind candidate state or alter the transaction. A true rewind starts a fresh V231 epoch.

This split is deliberate: donor semantics remain directly comparable to submitted V3.1 while the only public current seam is safe under selected-action retries.

## Focused contracts

The exact-head suite covers:

- submitted authority pins, OFF identity, and exact-bool activation;
- no early-cattle behavior at steps 190–215;
- exact late purchase gates and bounded SHEEP→COW substitution;
- confirmed pickup/place/site ownership and harvested-milk accounting;
- no invented MILK sale row;
- malformed current envelope/cardinality/scalar-hands fail-closed behavior;
- identical purchase and HARVEST retry idempotence;
- changed valid retry retirement of abandoned purchase/harvest effects;
- malformed same-step retry preserving candidate state and transaction byte-for-byte by value;
- rewind starting a fresh epoch.

## Exact-head gate

From this directory the dedicated workflow runs, on Python 3.11 and 3.12:

```bash
python -m py_compile \
  v231_late_current.py v231_late_current_safe.py \
  test_v231_late_current.py test_v231_late_retry_safe.py test_v231_retry_boundary.py
python -B -m unittest -v \
  test_v231_late_current.py test_v231_late_retry_safe.py test_v231_retry_boundary.py
python -O -B -m unittest -v \
  test_v231_late_current.py test_v231_late_retry_safe.py test_v231_retry_boundary.py
```

Any receipt from an earlier head is non-authorizing. The current successor must obtain a fresh exact-head normal/`-O`/compile/clean-tree receipt before merge.

## Promotion boundary

This carrier is research/source evidence only: no runtime/config/default/archive/release/Kaggle mutation. Promotion requires fresh matched current-V5 OFF vs `V231LateCurrentABISafe(enabled=True)` economics, then V231-late → existing gated S2 composition on the same panel if engagement survives.

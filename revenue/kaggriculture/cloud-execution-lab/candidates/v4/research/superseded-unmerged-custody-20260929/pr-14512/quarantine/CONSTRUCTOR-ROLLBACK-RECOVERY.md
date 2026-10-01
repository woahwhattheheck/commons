# Constructor rollback recovery packet

This is an additive support packet for the existing TITAN V4 optimizer-cache-lifetime work. It is **not** a second V4, a replacement optimizer stack, or a production/default activation.

Ownership remains unchanged: WEAVE owns the composed optimizer stack from #12743; CANOPY's lifetime gate and constructor-limit characterization landed in #12742; the Slack coordination thread records SPINDLE as constructor-integration owner. Do not install two constructor transformations.

## Recovered mechanism

`repair_constructor_rollback.py` authenticates the exact known `MarketPath.__init__` preimage, wraps construction in `try/except BaseException`, removes only partially installed `joint`, `single`, and `quote` cache attributes, and re-raises the original exception. The transformer is idempotent, rejects constructor drift, refuses in-place input/output aliasing, and leaves bytes outside the owned constructor unchanged.

This closes the characterized failure where cancellation during cache installation can retain the model before caller cleanup starts. It does **not** claim universal interruption safety: the constructor-return/caller-assignment boundary remains outside the protected region, and interruption during rollback itself is not guaranteed recoverable.

## Executed local evidence retained by recovery session

- Component suite: 18/18 normal and 18/18 under `python -O`, zero failures/errors/skips.
- Mutation suite: eight deliberately broken variants rejected in each mode by assertions rather than crashes/errors.
- Optimizer parity: 1,680 receipt/score comparisons and 162 optimizer/capacity-order pairs per mode.
- Existing CACHELIFE composition: required order is CACHELIFE then constructor rollback; reverse order correctly rejects source drift.
- Native parity: six complete games, seed 9922999, both seats, official starter, baseline vs CACHELIFE vs CACHELIFE+rollback. All 4,314 native calls completed with identical raw-action/cash/terminal-observation traces and terminal scores across arms.

The game panel is a parity/control certificate only, not a competitive-strength, current-HEAD, hosted-deadline, or speed claim.

## Existing authority

- WEAVE combined stack: #12743
- CANOPY lifetime gate / constructor-limit characterization: #12742
- Coordination thread: https://tokenjunkielabs.slack.com/archives/C0C0Z8AHGP2/p1789181661901419

This recovery branch publishes the previously stranded source as supporting material for the existing owner. Integration into the sole canonical V4 should occur only after comparison against SPINDLE's current constructor implementation; if SPINDLE already contains an equivalent fix, retain the tests/evidence and do not stack this transform.

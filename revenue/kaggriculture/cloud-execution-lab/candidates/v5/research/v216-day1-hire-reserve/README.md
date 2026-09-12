# V216 day-one HIRE reserve — current ABI recovery

This research carrier recovers the **submitted V3.1 V216 wrapper** without reviving the legacy router.

Exact submitted authority is `a90d888f03987ef0b35cfd20ec3519c6144db08a`,
Kaggle submission `56172377`, archive SHA-256
`5db3921f85efbc7596e5a1e7e198fc5f4644ceea43d8e8323c74ded7b4ba4361`.
The donor is `candidates/v3/overlay/r04_full_router.py` Git blob
`a3e2fe87c717d128e43c9b65bae2265f40d1d76d`.

V216 is active inside the submitted winner through `POLICY_AGENT`; it is not one
of the later R04 feature flags. Its exact decision theorem is intentionally tiny:

- public step must be **23**;
- the already-selected action must have an empty market;
- exact authored route row **24** must contain **1..5** `HIRE` market rows;
- required cash is the Fibonacci prefix `(1, 1, 2, 3, 5)` times
  `farmHandCostMult`;
- current own cash is below that requirement;
- projected post-unit shed has at least **3 WHEAT** (preserving two after sale);
- current WHEAT sell price covers the entire cash deficit;
- then and only then replace the empty market with exactly
  `[['SELL', 'WHEAT', 1]]`.

Projection preserves the donor's nearby-shed `PICKUP` / ordered-capacity `DROP`
/ non-animal `PLACE` semantics. All other selected-action bytes are preserved.

## Current ABI

The carrier never calls a producer/controller and never reads a legacy tape.
It consumes the already-selected current action plus the one immutable
`CurrentRouteWindow` landed by #13425 and hardened by #13434. At public step 23, row 0 of that v2 witness
is authenticated `R[committed_route_id][24]` from the producer route committed with the selected action; malformed/wrong-source/wrong-step
evidence fails closed to action identity. The pinned current witness blob is
`b84768c7560e746f6c9144fea672554e0dad39f7`.

`transform_with_report(...)` returns the transformed action plus a detached
research receipt; `transform(...)` is the action-only surface. Neither mutates
caller inputs.

V217 is deliberately **not** included here: historical score work falsified that
idle-farmer starvation rescue, so this carrier recovers only the V216 behavior
actually worth re-evaluating on current V5.

This is source/evidence only. It does **not** change runtime defaults,
`TITAN-CONFIG.json`, CURRENT/archive pointers, release authority, or Kaggle
submission. Promotion requires natural engagement plus matched current-V5
economics under the single R04/V5 convergence line.

Focused contracts:

```bash
python -B -m py_compile v216_day1_hire_reserve.py test_v216_day1_hire_reserve.py
python -B -m unittest -v test_v216_day1_hire_reserve.py
python -O -B -m unittest -v test_v216_day1_hire_reserve.py
```

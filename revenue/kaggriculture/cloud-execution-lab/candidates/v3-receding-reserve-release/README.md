# TITAN V3 — receding shed-reserve release

Operation: `titan-v3-receding-reserve-release-20260909-01`  
Worker: **SOL-LEVEL**

## Why this exists

The preserved Arlene seller deliberately keeps one shed slot open: its capacity
policy targets 99 of 100, not the engine's legal maximum. That reserve is useful
when the next unit stage can `DROP` or `PLACE` inventory before the next market,
or when an incoming product/animal purchase needs room.

The blanket change `cap - 1 -> cap` is therefore rejected.

This candidate tests a narrower receding-horizon proposition. Only the current
action is emitted. The agent is called again before the next unit stage, but a
market sale cannot rescue that next unit stage because units execute first. It
is safe to carry exactly 100/100 for one step only when the represented next
stage cannot add shed load.

## Admission certificate

`reserve_release_certificate` fails closed unless all of these hold:

1. The unbounded projection of the **current** unit stage is exactly the real
   shed capacity. Lower occupancy keeps the predecessor fast path; a current
   `DROP` overflow can never be repaired by a later market sale.
2. Titan's dynamic selected-unit producer is explicitly idle/unbound for this
   seller call; an active spatial/crop continuation keeps the reserve.
3. The exact next route action exists before the terminal boundary.
4. The next step is not a public route-selection checkpoint and does not cross
   a day boundary.
5. No next actor action is `DROP` or `PLACE`.
6. Neither the current nor next **executable market prefix** contains
   `BUY_PRODUCT` or `BUY_ANIMAL`.

When the certificate passes, the inherited receipt profile is evaluated twice:
first unchanged, then—only at exact-full current occupancy—with synthetic
capacity `real + 1`. Because the inherited
seller still reserves one slot, the second run changes only the later occupancy
bound from `real - 1` to `real`. The current unbounded projection remains bound
to the real capacity by condition 1. The result is `baseline(plan) OR
relaxed(plan)`, so no previously feasible plan is removed.

Unknown state, malformed actions, another installed receipt-profile owner,
branch boundaries, day boundaries, dynamic unit-producer work, true overflow,
deposit-capable unit actions,
and incoming shed purchases all retain the original 99/100 policy.

## Exact source boundary

The branch began from Commons main
`5c202d3d471e77df2bcbf4add371fa2b8aaaf308`.

- `scheduler.py` Git blob:
  `a483b24dd72b580d7d8811636b54d2d44f391575`
- pinned official engine `kaggriculture.py` Git blob:
  `3c202c7ee921da239356789e266b694635103fc4`
- preserved Arlene source documents the deliberate one-slot reserve.
- official engine evidence proves a purchase may reach exactly 100/100 and a
  further purchase is then rejected.

The implementation is additive under this directory. It does not edit
`scheduler.py`, `frozen_selected.py`, `titan_runtime.py`, `main.py`,
`TITAN-CONFIG.json`, archives, release pointers, or provider state.

## Verification

Focused contracts cover:

- official-engine 99 -> 100 admission and blocked 100 -> 101 purchase;
- predecessor rejection versus candidate admission at safe exact-full carry;
- current pre-market overflow remaining rejected;
- next `DROP` and `PLACE` retaining the spare slot;
- current/next incoming product or animal purchases retaining the spare slot;
- active-prefix, malformed active-market rows, fixed 24-turn semantics,
  route-checkpoint, day-boundary, no-mutation, idempotent install, existing
  `FrozenSelected` inheritance, and peer-patch collision behavior;
- loader discovery proving all 14 reserve-release contracts are class-level tests;
- the inherited 5-test paired comparator suite plus a separate 5-test strict
  own-cash gate, so rival harm cannot disguise a candidate cash loss;
- fail-closed paired-report completeness, provenance, digest, finite-number,
  duplicate-cell, trace-only/no-effect, own-cash, and margin-regression gates.

Local command:

```bash
cd revenue/kaggriculture/cloud-execution-lab/candidates/v3-receding-reserve-release
PYTHONDONTWRITEBYTECODE=1 python -m unittest -v \
  test_reserve_release.py test_compare_panel.py test_strict_gate.py
```

The path-scoped workflow additionally runs current control and candidate through
the pinned official interpreter against public Arlene and submitted V1, both
seats, on the same development seeds. The original comparator must first
accept complete, provenance-bound, no-regression margin evidence; the independent
`strict_gate.py` must then prove at least one changed cell, positive mean paired
own cash and paired margin, and no negative own-cash or margin cell. A trace-only
change with no cash signal is `HOLD`; `NO_SIGNAL` keeps the candidate isolated.
Any incomplete, duplicate, extra, nonfinite, or provenance-drifted cell is
`INVALID`.

This is development evidence only. It is not a hosted leaderboard result and
does not authorize canonical promotion.

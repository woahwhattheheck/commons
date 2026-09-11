# TITAN V3.1 — H4 × horizon-10 on frozen-canonical custody

This directory is an **evaluation-only stacked experiment** on the reviewed H4 live-R04 strawberry top-up source. It does not change H4 logic, shipped V3 defaults, `overlay/**`, deterministic package inputs, provider state, or Kaggle/submission state.

## Exact topology

This carrier is a direct child of #12419 exact head `0ac88a0c210c0c52ef9da53de85dd1c0528d8eae`, which mechanically replays the six reviewed H4 blobs onto #12392 frozen-canonical/package-integrity custody. L3 is absent.

The executable interaction bytes are copied **byte-for-byte** from #12409:

- `candidate.py` blob `f681eb8f491d8211565bcd92a3ecaac13cb89a1f`
- `test_h4_horizon10.py` blob `27de1829c33aa9ec5f0639b8e9e5f2b8b22de1f8`

Only this README and the carrier workflow are rewritten to bind the new parent/custody topology.

## Exact factor

The control is H4 with the live V3.1 R04 tuple and `r04_sale_horizon=8`. The candidate keeps every other R04 knob identical and changes only:

```text
r04_sale_horizon: 8 -> 10
```

H4 remains enabled in both arms. This isolates whether the strong standalone horizon-10 signal survives or compounds with H4 rather than attributing an H4 effect to the horizon change.

## Source/custody gate

The dedicated workflow binds exact parent `0ac88a0c...`, rejects any diff outside these four additive files, reruns H4's 13 focused predecessors, runs the two H4+h10 custody tests, compiles the exact evaluator entrypoint, runs `build_v3.py --check` against the frozen-canonical topology, and requires a clean checkout.

## Economics boundary

This carrier makes **no new score or promotion claim**. Required execution remains H4+h10 versus identical H4+h8 on the exact official interpreter/materialized-package custody, same opponent bytes, frozen seeds `2611151001..2611151008` both seats, followed by the representative live-opponent mixture if the frozen screen is green.

Report paired competitive `ΔM`, own/rival deltas, W/T/L transitions, every negative cell, process failures, and H4 activation/debt telemetry. A positive H13 standalone result is not H4×h10 interaction evidence.

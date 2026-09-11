# TITAN V3.1 — H4 × horizon-10 interaction arm

This directory is an **evaluation-only stacked experiment** on the reviewed H4 live-R04 strawberry top-up source. It does not change H4 logic, shipped V3 defaults, `overlay/**`, deterministic package inputs, provider state, or Kaggle/submission state.

## Exact factor

The control for this interaction is H4 with the live V3.1 R04 tuple and `r04_sale_horizon=8`. The candidate keeps every other R04 knob identical and changes only:

```text
r04_sale_horizon: 8 -> 10
```

H4 remains enabled in both arms. This isolates whether the strong standalone horizon-10 signal survives or compounds with H4 rather than attributing an H4 effect to the horizon change.

## Required economics gate

Run the exact official interpreter/materialized package custody used by the current V3.1 fidelity standard, with the same opponent bytes in both arms. First screen the frozen seeds `2611151001..2611151008`, both candidate seats, comparing **H4+h10 vs H4+h8**. Report paired `ΔM`, own/rival deltas, W/T/L transitions, every negative cell, process failures, and H4 activation/debt telemetry.

A positive mean alone is not promotion authority. HOLD if the interaction creates new losses, if H4 activations are suppressed or duplicated in a way that cannot be explained by the horizon change, or if exact opponent/config/package custody cannot be proven. If the frozen interaction screen survives, widen to the same representative-opponent mixture used for the L3 disposition work before any default/package decision.

## Custody boundary

This branch is stacked on H4 exact head `70b04f34731fb0f3e1bf7640b500ad6228ca4dd2`. The only new executable file is `candidate.py`; it imports the reviewed H4 module and uses its existing validated `install()` seam. The companion focused test verifies the exact interaction config and runtime horizon/H4 flags. Package-integrity closure remains owned by the current frozen-canonical carrier rather than being reimplemented here.

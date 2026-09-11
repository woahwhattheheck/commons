# H7 — R04 rival early-expander response

Status: **experiment / evaluator arm only**. No default, package, or Kaggle submission change.

## Source-grounded seam

V3 already ships `overlay/rival_model.py` (O01). It reads only public rival state and may append one `BUY_LAND` when:

- `step <= g01_early_expander_step` (default 144),
- the rival has unlocked more than one quadrant,
- our farm still has only `NW`,
- current cash covers the next land price plus `g01_land_cash_floor`,
- no `BUY_LAND` is already queued, and
- the market queue has a free row.

The integrated canonical controller invokes O01 in `TitanAgent._v3_post`. R04 is a whole-route delegate (`_v3_r03_act`) and returns without traversing `_v3_post`, so the live V3 R04 route never consumes the existing `rival_model` key.

H7 does **not** invent a new opponent classifier or new capital rule. `experiments/h7_r04_rival_response.py` reuses `rival_model.apply_rival_model` unchanged and wraps the *final* installed R04 callable.

## Why the wrapper is last

R04 postprocessing currently performs `ROW_ORDER`, then `EVENING_FLUSH`, then the optional step-0 opening replacement. H7 runs after all three. This gives those existing policies priority over the 10-row market cap. O01 can only append `BUY_LAND` if the resulting final queue still has capacity; it cannot evict a flush row or suppress the opening replacement.

Disabled H7 returns the exact parent output object.

## Evidence target

Replay motivation is the live Kaggriculture Agent loss in which the rival deployed roughly twice Titan's spend and won on production volume. V3.1's cattle change already flips that historical cell positive, so H7 must justify itself on a broad panel rather than that anecdote.

Required before production wiring or merge:

1. Focused contract checks green.
2. Run the same 41-live-game pinned-opponent panel used for V3.1, paired against exact V3.1.
3. Report competitive margin `ΔM = Δown - Δrival`, activation count, changed-action count, and every negative cell.
4. Reject if mean `ΔM < 0`, if gains are only an artifact of row displacement, or if a live activation violates queue/cash ownership assumptions.
5. If promoted into `overlay/**` / `apply_v3.py`, regenerate deterministic manifests and require `build_v3.py --check`; this experiment intentionally does not modify package inputs.

## Bench hook

Use the exact installed R04 callable as the parent:

```python
from h7_r04_rival_response import install as install_h7

candidate = install_h7(exact_v31_r04_callable, enabled=True)
```

The returned callable exposes `.telemetry` with calls, changed-action count, archetype counts, and reason counts for activation auditing.

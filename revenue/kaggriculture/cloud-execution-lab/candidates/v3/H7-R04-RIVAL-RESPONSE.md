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

## Why the wrapper is last — and the execution caveat

R04 postprocessing currently performs `ROW_ORDER`, then `EVENING_FLUSH`, then the optional step-0 opening replacement. H7 runs after all three. This gives those existing policies priority over the 10-row market cap: O01 cannot evict a flush row or suppress the opening replacement.

However, canonical O01 normally runs **before** downstream `_finish_production` / `early_capital` ordering. A final-R04 wrapper does not inherit that capital-ordering stage. Therefore an H7 `BUY_LAND` edit is only a **proposal**: an earlier executable HIRE/BUY row may consume observation-start cash before the appended land row executes. The focused predecessor is exactly `$1000` cash + earlier `HIRE` + EARLY_EXPANDER rival: H7 may append `BUY_LAND`, but that must not be counted as an executed purchase.

Telemetry therefore separates:

- `changed` / `proposals`: action mutations only; **not activation/execution**,
- `confirmed_unlocks`: a later public observation has more owned quadrants than at proposal time,
- `no_unlock_next_observation`: proposal was followed by a later observation without an unlock,
- `reset_with_pending`: episode reset discarded an unresolved proposal outcome.

Disabled H7 returns the exact parent output object.

## Evidence target

Replay motivation is the live Kaggriculture Agent loss in which the rival deployed roughly twice Titan's spend and won on production volume. V3.1's cattle change already flips that historical cell positive, so H7 must justify itself on a broad panel rather than that anecdote.

Required before any production wiring or merge:

1. Focused contract checks green, including the earlier-cash-spend predecessor above.
2. Run the same 41-live-game pinned-opponent panel used for V3.1, paired against exact V3.1.
3. Report competitive margin `ΔM = Δown - Δrival`, `proposals`, `confirmed_unlocks`, `no_unlock_next_observation`, proposal→unlock conversion, archetype/reason counts, and every negative cell.
4. **Reject zero confirmed unlocks even if proposals are nonzero.** Proposal count must never be reported as activation count.
5. Reject if mean `ΔM < 0`, if gains are only an artifact of row displacement, or if any recurrent live activation violates queue/cash ownership assumptions.
6. This final-output placement is not itself production-safe merely because economics are positive. Production wiring must restore an execution-safe capital composition seam (or prove equivalent behavior) and receive a fresh predecessor review.
7. If promoted into `overlay/**` / `apply_v3.py`, regenerate deterministic manifests and require `build_v3.py --check`; this experiment intentionally does not modify package inputs.

## Bench hook

Use the exact installed R04 callable as the parent:

```python
from h7_r04_rival_response import install as install_h7

candidate = install_h7(exact_v31_r04_callable, enabled=True)
```

The returned callable exposes `.telemetry` for proposal/outcome, archetype, and reason auditing.

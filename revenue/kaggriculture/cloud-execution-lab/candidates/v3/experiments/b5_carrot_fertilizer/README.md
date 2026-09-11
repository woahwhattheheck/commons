# B5 — no-detour CARROT fertilizer

Evaluation-only V3.1 experiment. This directory is outside `overlay/**`, so it is not
included by `build_v3.py` and changes no production default or submission artifact.

## Mechanism

The pinned interpreter makes fertilizer a three-day top-up: `FERTILIZE` consumes one
carried `FERTILIZER` and extends `fertilized_until_day` through `day + 2`; watered crop
yield can then receive the fertilizer bonus. The experiment refuses to create any route,
purchase, hire, market row, or non-idle worker command. It changes only an existing
`PASS` when all of these are already true:

- the worker is standing on a `CARROT` plant;
- the worker is already carrying fertilizer;
- the tile is not already fertilized through `day + 2`;
- at most one worker claims a tile in the same action.

The evaluator arm explicitly pins the live V3.1 R04 baseline tuple: horizon 8, opening 0,
row-order ON, evening-flush ON, sale-fertilizer ON, cattle-early ON.

## Why the scope is narrow

Broader B5 variants were not safe on the frozen Arlene screen. The initial no-detour
all-crop rule averaged `+81.625` competitive margin but had a `-137` cell. On that cell,
WHEAT-only was `-314` while STRAWBERRY-only was `+81` and CARROT-only `+45`.
Removing WHEAT improved the mean to `+123.1875` but still left four negative cells;
the remaining regressions isolated to STRAWBERRY (for example `-55` on seed 1005 and
`-93/-84` on seed 1008). CARROT-only is the first tested predicate with every frozen
cell positive. Do not generalize this experiment back to a blanket fertilizer sweep
without new evidence.

## Mechanism screen — frozen Arlene panel

Interpreter ref: `28b6d8af3ce73926b3d0fda1410c1ddd8384ab8c`.
Opponent: vendored Arlene, entry SHA-256
`1dc166ae2bf0c56a44fac4482f469b8812968c4cb32459cb9860f5077897a7d4`.
Seeds: `2611151001..2611151008`, both candidate seats.

| seed | seat 0 ΔM | seat 1 ΔM |
|---:|---:|---:|
| 2611151001 | +63 | +63 |
| 2611151002 | +112 | +112 |
| 2611151003 | +40 | +40 |
| 2611151004 | +45 | +45 |
| 2611151005 | +25 | +25 |
| 2611151006 | +98 | +98 |
| 2611151007 | +264 | +264 |
| 2611151008 | +66 | +66 |

Result: **16/16 positive**, mean ΔM **+89.125/game**, range **+25..+264**, zero
candidate/opponent failures. Baseline mean margin was `8356.6875`; candidate mean margin
was `8445.8125`.

Exact source used for the rerun has SHA-256
`191febc1c751c6553103b92411f0a1f4a5942e69d39d6c8c6d8d61260f2ee4a4`.
The recovered handoff archive was
`8fb4776b416f32dcd978f57a6f8caf42c84d2245d5f9a08962adbe814dadab8e`; its ready-submit
inner archive was `e4e5a3acfe4984c89c22c7aa841b4ddd6efe4f4cd71e507d1dabecbb6e865849`.

### Fidelity boundary

This is **mechanism-screen evidence, not an official 1:1 promotion gate**. The candidate
was run against the exact recovered ready-submit V3.1 tree and pinned official
interpreter, but this screen did not rematerialize the candidate from the
manifest-pinned canonical archive through `build_v3.py`. Under the current SIM FIDELITY
STANDARD, promotion still requires that strict build custody, the frozen panel, live
config, and exact opponent fingerprint in one reproducible receipt.

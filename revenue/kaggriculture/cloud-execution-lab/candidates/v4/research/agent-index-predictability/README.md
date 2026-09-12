# Agent-index predictability

Research-only tooling for measuring whether the target agent's player/seat index predicts outcome after controlling for seed and opponent identity. This lane does **not** change gameplay, defaults, production code, or Kaggle activation.

## Why matched pairs

A pooled seat-0 vs seat-1 average is not trustworthy when opponent assignment differs by seat. The analyzer therefore treats the primary observation as an exact `(seed, opponent)` pair with the target run once in seat 0 and once in seat 1. It reports the target-margin delta `seat1 - seat0`, plus an equal-opponent-weighted mean so a frequently sampled opponent cannot dominate the conclusion.

It also reports raw opponent-assignment total-variation distance and matched-pair coverage. Large assignment TV or poor coverage is a warning that unpaired seat averages are confounded.

## Input

JSON array or JSONL. Each record needs:

- seed: `seed`, `episode_seed`, or `game_seed`;
- opponent identity: `opponent`, `opponent_id`, or `opponent_name`;
- target seat: literal integer 0 or 1 in `target_seat`, `seat`, `player_index`, `agent_index`, or `player`;
- outcome as one of:
  - target-relative `margin`,
  - two-item `rewards` list (the analyzer picks target/opponent by seat), or
  - `score` + `opponent_score`.

Duplicate exact `(seed, opponent, seat)` cells fail closed. `--require-complete` rejects any seed/opponent group missing one seat.

Example:

```json
{"seed":1909087201,"opponent":"LARK","seat":0,"rewards":[101200,99800]}
{"seed":1909087201,"opponent":"LARK","seat":1,"rewards":[99800,101200]}
```

## Output

The JSON report includes exact matched-pair coverage; matched seat-0 / seat-1 mean target margins; paired mean and median `seat1 - seat0` delta; equal-opponent-weighted mean delta; paired sign-test counts and exact two-sided p-value; Cohen's paired standardized effect where finite/defined; per-opponent pair counts and mean deltas; raw opponent-assignment total-variation distance; and missing-cell examples.

A constant nonzero paired delta has zero variance and therefore no finite Cohen `d_z`; the tool emits JSON `null` for that degenerate statistic while preserving the raw paired mean and sign test.

## Verification receipt

Analyzer Git blob `42f78767d87101cbc350d1aff47c73d2e345c3d9`, SHA-256 `64297377e42c3d629ef6b7a4decb8b44364db81b15d35e8daaae6e5d7326a394`.

Regression Git blob `87161821a9b617f205d5a9030b69cb6919ac7375`, SHA-256 `167bee0e43e521982186ab982fe1914efbb69d3db754cc635b9f3c60da27713c`.

Local verification before landing: 8/8 tests PASS under both normal Python and `python -O`. Tests include Simpson's-paradox opponent mix, unequal opponent-frequency weighting, exact duplicate/missing-cell rejection, seat-relative reward interpretation, strict type/finite-number handling, and strict-JSON zero-variance effect handling.

At initial landing, default-branch searches did not surface a committed replay corpus containing the required matched seed/opponent/seat/outcome cells. A replay-capable/data seat should run this analyzer against an exact paired panel rather than infer a result from unmatched hosted games.

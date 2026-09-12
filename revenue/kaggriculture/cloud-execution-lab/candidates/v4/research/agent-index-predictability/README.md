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

If a record contains more than one outcome representation, all supplied representations must agree (within tight floating-point tolerance) or the record fails closed. When they agree, the analyzer prefers `rewards`, then `score` + `opponent_score`, over a direct `margin`. This prevents a contradictory self-reported margin from silently overriding structured score fields while preserving legitimate large finite engine rewards; there is deliberately no guessed reward ceiling.

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

Analyzer Git blob `db32c109b61af72917e302c0cdf69014d284afc1`, SHA-256 `0a56bf369c84e9412a69ae199bd1a41b38a7d7c9105227bae82e5f56b4402219`.

Regression Git blob `8a9501cbfb1d90a7b03c81ab463e1202b661c6f1`, SHA-256 `ed288e4e8ce9dd7df7e603e0dbc75c476c7b15976c9a4ab228fa05bd9647c058`.

Local verification before publishing: 13/13 tests PASS under both normal Python and `python -O`. Tests include Simpson's-paradox opponent mix, unequal opponent-frequency weighting, exact duplicate/missing-cell rejection, seat-relative reward interpretation, strict type/nonfinite/overflow handling, contradictory redundant outcome rejection, consistent redundant outcome acceptance, a legitimate 165,022-margin reward control, and strict-JSON zero-variance effect handling.

At initial landing, default-branch searches did not surface a committed replay corpus containing the required matched seed/opponent/seat/outcome cells. A replay-capable/data seat should run this analyzer against an exact paired panel rather than infer a result from unmatched hosted games.

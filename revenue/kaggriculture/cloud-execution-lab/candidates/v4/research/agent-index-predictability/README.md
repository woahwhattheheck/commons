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

If a record contains more than one outcome representation, all supplied representations must agree exactly after numeric validation or the record fails closed. There is deliberately no relative-tolerance comparison here: without an authenticated magnitude bound, a tiny relative difference can still be an enormous absolute contradiction. Integer values are retained exactly after finite-range validation so disagreements above the IEEE-754 exact-integer range cannot collapse through float conversion. When representations agree, the analyzer prefers `rewards`, then `score` + `opponent_score`, over a direct `margin`. This prevents a contradictory self-reported margin from silently overriding structured score fields while preserving legitimate large finite engine rewards; there is deliberately no guessed reward ceiling.

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

Analyzer Git blob `c6cf14817096867bc66968598cf5a64f2e928ad2`, SHA-256 `316464ec07c730da0fe953b6f1f6078bbdb8570863c0ae10ecb82349e7093bd4`.

Regression Git blob `439ee93afc663e539c227635f8197a337fbec782`, SHA-256 `a7a58a1bd8d09b22992e89cb96916aac83b0e7f9ca93cb94d97d7e867bd0d748`.

Exact-byte local verification before publishing: 15/15 tests PASS under both normal Python and `python -O`. Tests include Simpson's-paradox opponent mix, unequal opponent-frequency weighting, exact duplicate/missing-cell rejection, seat-relative reward interpretation, strict type/nonfinite/overflow handling, contradictory redundant outcome rejection, a large-magnitude conflict that the predecessor's relative tolerance accepted, a `10**20` versus `10**20+1` integer-collapse killer, consistent redundant outcome acceptance, a legitimate 165,022-margin reward control, and strict-JSON zero-variance effect handling.

At initial landing, default-branch searches did not surface a committed replay corpus containing the required matched seed/opponent/seat/outcome cells. A replay-capable/data seat should run this analyzer against an exact paired panel rather than infer a result from unmatched hosted games.

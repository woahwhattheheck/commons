# TITAN rating-aligned promotion gate

This package separates **rating evidence** from **cash polish** in matched TITAN panels.

Several current candidate screens can report positive own cash and margin while every terminal result stays `W→W` or `L→L`. That is useful economic evidence, but it is not evidence that a candidate can improve leaderboard rating. This gate makes terminal win/tie/loss movement the primary decision variable and keeps cash/margin as diagnostics.

It reuses the terminal point convention already established by PR #9992:

- win = 1 point
- tie = 1/2 point
- loss = 0 points

## Verdicts

- `RATING_ADVANCE_SCREEN`: positive paired terminal win-point delta; no adverse outcome cell; no new loss or lost win; every opponent × seat stratum is nonnegative; every score-changing cell has a changed tested-seat action digest.
- `POLISH_ONLY`: no terminal outcome changes; action-active; own cash improves; margin is nonnegative; no negative own-cash cell or cash/margin stratum.
- `MORE_EVIDENCE`: action-active evidence that satisfies neither strict rating nor strict polish criteria.
- `NO_SIGNAL`: identical tested-seat action streams and scores in every pair.
- `REJECT`: any adverse paired outcome, global win-point regression, or opponent × seat win-point regression.
- `INVALID`: malformed, incomplete, duplicated, lifecycle-invalid, or causally unbound evidence.

`RATING_ADVANCE_SCREEN` is deliberately a screen, not a leaderboard or deployment claim. The output also reports an exact paired one-sided sign-test fraction and labels broad versus concentrated signal; it never converts a small panel into a fabricated Elo estimate.

## Input contract

The classifier consumes normalized JSON, not arbitrary panel layouts. A producer adapter must orient scores to the tested candidate seat before creating this document.

```json
{
  "schema": "titan.rating-gate.input.v1",
  "experiment": {
    "control_id": "control source identity",
    "candidate_id": "candidate source identity",
    "engine_sha256": "64 lowercase hex",
    "evaluator_sha256": "64 lowercase hex",
    "opponent_manifest_sha256": "64 lowercase hex",
    "grid_id": "immutable grid identity"
  },
  "pairs": [
    {
      "opponent": "arlene",
      "seed": 2609097301,
      "seat": 0,
      "control": {
        "state": "complete",
        "phase": "finalize",
        "own_score": 100,
        "rival_score": 120,
        "tested_action_sha256": "64 lowercase hex",
        "action_count": 719
      },
      "candidate": {
        "state": "complete",
        "phase": "finalize",
        "own_score": 130,
        "rival_score": 120,
        "tested_action_sha256": "64 lowercase hex",
        "action_count": 719
      }
    }
  ]
}
```

The gate rejects duplicate JSON keys, duplicate `(opponent, seed, seat)` cells, non-finite scores, non-finalized games, wrong action cardinality, invalid hashes, identical control/candidate identities, and any score change under an identical tested-seat action digest.

## Usage

```bash
python -B rating_gate.py paired-report.json --output rating-verdict.json
python -B rating_gate.py paired-report.json \
  --require-verdict RATING_ADVANCE_SCREEN \
  --output rating-verdict.json
```

Exit status is `0` for structurally valid evidence unless `--require-verdict` is supplied, `2` for invalid evidence, and `3` when a required verdict is not met. This keeps infrastructure failure distinct from an honest experimental rejection.

## Tests

```bash
python -B -m unittest -v test_rating_gate.py
```

The adversarial suite covers cash-only false advancement, large cash masking a new loss, mixed opponent/seat outcomes, action-identity score drift, duplicate/incomplete cells, exact 719-action lifecycle, deterministic receipts, and valid `L→W` / `T→W` movement.

## Scope

Evidence analysis only. No policy, agent runtime, configuration, archive, release pointer, game launch, provider, Kaggle submission, or spending behavior is changed.

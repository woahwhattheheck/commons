# TITAN version regression microscope

`regression_microscope.py` is a dependency-free, fail-closed analyzer for exact
V1/V2/V3 paired game evidence. It answers the owner-facing question that a
leaderboard number cannot answer by itself: **what was the first TITAN action
that changed, and was that tested-seat change actually responsible for better
or worse terminal performance?**

It never runs a game, imports a policy, calls Kaggle, or edits a release. It
consumes retained evidence produced by the official evaluator.

## Why this exists

A whole-game trace digest covers both agents, state evolution, bank changes,
and often observations. Therefore `trace_a != trace_b` is not proof that the
TITAN arm under test activated. Likewise, a margin gain is not a TITAN gain
when TITAN's own terminal cash fell and only the rival fell farther.

The microscope instead enforces all of the following per exact
`opponent × seed × candidate-seat` cell:

- exactly 719 tested-seat returned actions (configurable only for unit fixtures);
- complete/finalized evaluator lifecycle;
- identical engine and opponent source identities;
- an exact SHA-256 over the tested-seat action sequence;
- action identity implies terminal-world, full-trace, and both-score identity;
- action divergence implies full-trace divergence;
- candidate-own cash is primary, while margin and W/T/L must be coherent;
- no score from one cell may be attributed to activation in another cell.

For three versions it emits V1→V2 harm, V2→V3 repair, and V1→V3 net reports,
then clusters repeated harmful first-divergence signatures. For leave-one-out
feature arms, the exact all-enabled config bytes must match the pinned control
hash and the disabled arm must differ at exactly one `true→false` feature path.
Only then can `candidate_disable` be emitted, and only when the arm has an
action-bound positive own-cash signal, no negative own-cash cell, no new/lost
wins, nonnegative margin, and nonnegative opponent×seat strata.

## Input contract

```json
{
  "schema": "titan-regression-microscope/v1",
  "expected_action_count": 719,
  "three_way": ["v1", "v2", "v3"],
  "feature_arms": {
    "control": "v25_all_enabled",
    "canonical_control_config_sha256": "... exact archived control bytes ...",
    "feature_path": ["features"],
    "disabled": {
      "funding": "v25_no_funding"
    }
  },
  "versions": {
    "v1": {
      "identity": {
        "source_sha256": "...",
        "archive_sha256": "...",
        "config_sha256": "...",
        "config_text": "{\"features\":{\"funding\":true}}"
      },
      "cells": [
        {
          "opponent": "Arlene",
          "seed": 9921001,
          "seat": 0,
          "state": "complete",
          "phase": "finalize",
          "engine_sha256": "...",
          "opponent_sha256": "...",
          "tested_seat_actions": ["... exactly 719 returned actions ..."],
          "tested_action_sha256": "...",
          "terminal": {
            "own_cash": 100000,
            "rival_cash": 90000,
            "terminal_world_sha256": "...",
            "full_trace_sha256": "..."
          }
        }
      ]
    },
    "v2": {"identity": {"source_sha256": "...", "archive_sha256": "...", "config_sha256": "..."}, "cells": []},
    "v3": {"identity": {"source_sha256": "...", "archive_sha256": "...", "config_sha256": "..."}, "cells": []}
  }
}
```

Each version must contain the same exact cell grid. `own_score` and
`rival_score` may be supplied when the official objective differs from cash;
otherwise cash is used.

## Run

```bash
python3 -B regression_microscope.py evidence.json \
  --json-out regression-report.json \
  --markdown-out regression-report.md
python3 -B -m unittest -v test_regression_microscope.py
```

Exit code `2` means the input failed an exactness or lifecycle contract. No
partial report is emitted.

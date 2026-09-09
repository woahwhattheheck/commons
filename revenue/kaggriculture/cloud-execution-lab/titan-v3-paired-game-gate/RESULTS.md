# Verification receipt

Operation: `titan-v3-paired-game-gate-20260909-sol-argus-02`

## Executed before publication

```text
PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 \
  python3 -m unittest -v test_validation.py test_policy_cli.py

Ran 23 tests
OK
```

```text
python3 -m compileall -q .
PASS
```

```text
python3 gate.py \
  --contract example/CONTRACT.json \
  --evidence example/PROVENANCE.json \
  --baseline example/canonical.GAMES.jsonl \
  --candidate example/challenger.GAMES.jsonl \
  --report /tmp/titan-v3-example-gate.json --quiet

exit 0; verdict PROMOTE; cells 8; mean own delta 10.0
```

The example is synthetic interface evidence only. No official game, hosted run,
Kaggle submission, leaderboard query, runtime mutation, archive replacement, or
promotion action was performed.

## Adversarial coverage

The test suite proves fail-closed behavior for:

- missing, extra, duplicate, failed, and timed-out cells;
- baseline failures as well as candidate failures;
- non-finite values, malformed score cardinality, and invalid seats;
- duplicate JSON object keys and duplicate seed declarations;
- omission of either candidate seat;
- provenance mismatch and terminal symlink substitution;
- a positive global cash mean hiding a W-to-L regression;
- a positive global cash mean hiding a negative opponent stratum;
- an unchanged candidate when change is required;
- a worst-cell loss beyond the frozen policy floor;
- deterministic repeated reports and atomic CLI output;
- stable exit 0 (`PROMOTE`), exit 2 (`INVALID`), and exit 3 (`REJECT`).

## Explicit non-claims

- No candidate gameplay strength was measured.
- No statistical confidence or holdout generalization is claimed.
- No policy thresholds are asserted to be universally correct.
- No release pointer or canonical Titan artifact is changed.

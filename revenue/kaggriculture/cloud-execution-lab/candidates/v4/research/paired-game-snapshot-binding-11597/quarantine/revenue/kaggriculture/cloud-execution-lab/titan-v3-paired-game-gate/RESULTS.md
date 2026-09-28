# Verification receipt

Parent operation: `titan-v3-paired-game-gate-20260909-sol-argus-02`

Snapshot-binding operation:
`titan-v3-paired-game-gate-snapshot-binding-20260909-sol-kiln-01`

Integrated numeric-closure operation:
`titan-v3-paired-game-numeric-closure-20260909-sol-cipher-01`

## Executed on the composed bytes before publication

```text
PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 \
  python3 -m unittest -v \
  test_validation.py test_policy_cli.py test_numeric_closure.py

Ran 30 tests in 3.138s
OK
```

```text
python3 -m compileall -q .
PASS
```

The path-race contract snapshots a valid candidate file and then truncates its
original path before parsing begins. The gate still reports the SHA-256 and byte
count of the preimage and evaluates that same preimage. This directly exercises
the prior hash-then-reopen time-of-check-to-time-of-use defect.

The numeric contracts drive three syntactically valid JSON cases through the
real CLI: an integer too large for binary float conversion, finite endpoints
whose subtraction becomes infinite, and finite per-cell deltas whose two-seat
mean overflows. Each exits 2 and persists a machine-readable `INVALID` report.

The example and test fixtures are synthetic interface evidence only. No official
game, hosted run, Kaggle submission, leaderboard query, runtime mutation,
archive replacement, or promotion action was performed.

## Adversarial coverage

The test suite proves fail-closed behavior for:

- missing, extra, duplicate, failed, and timed-out cells;
- baseline failures as well as candidate failures;
- non-finite values, scalar conversion overflow, derived subtraction/mean
  overflow, malformed score cardinality, and invalid seats;
- duplicate JSON object keys, boolean schema versions, and duplicate seed
  declarations;
- omission of either candidate seat;
- provenance mismatch and terminal symlink substitution;
- replacement of an original input after its single-open snapshot;
- a positive global cash mean hiding a W-to-L regression;
- a positive global cash mean hiding a negative opponent stratum;
- an unchanged candidate when change is required;
- a worst-cell loss beyond the frozen policy floor;
- deterministic repeated reports and atomic CLI output;
- stable exit 0 (`PROMOTE`), exit 2 (`INVALID`), and exit 3 (`REJECT`).

## Attribution and receipt correction

The arithmetic closure was independently authored on SOL-CIPHER PR #11603 head
`23fd92cb015eda1ea7c04253972bd0c93364b20a`. Its executable logic and three CLI
regressions were composed with the snapshot-binding branch. The source manifest
here was regenerated from the composed bytes rather than copying PR #11603's
stale metadata.

## Explicit non-claims

- No candidate gameplay strength was measured.
- No statistical confidence or holdout generalization is claimed.
- No policy thresholds are asserted to be universally correct.
- No release pointer or canonical Titan artifact is changed.

# Verification receipt

Operation: `titan-v3-measured-champion-firewall-20260909-sol`

## Executed before publication

```text
PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 \
  python3 -B -m unittest -v \
  revenue/kaggriculture/cloud-execution-lab/test_release_admission.py

Ran 29 tests in 0.104s
OK
```

```text
python3 -m compileall -q \
  revenue/kaggriculture/cloud-execution-lab/release_admission \
  revenue/kaggriculture/cloud-execution-lab/test_release_admission.py

PASS
```

```text
PyYAML safe_load(.github/workflows/titan-measured-champion-guard.yml)
PASS
```

## Covered transition failures

- release pointer changed while the ledger is first installed;
- pointer mutation without a measured ledger transaction;
- champion mutation without a pointer transition;
- policy weakening or policy/promotion coupling;
- alternate entrypoint substitution;
- current archive or source-manifest digest drift;
- historical champion symlink substitution;
- traversal and duplicate-key ambiguity;
- rejected, incomplete, one-seat, or under-sized gate evidence;
- missing and failed robustness checks;
- malformed engine/runner identity;
- evidence-input digest or byte-count mismatch;
- downgrade from the hardened single-open private-snapshot binding;
- stale source metadata with no explicit admission record;
- source metadata claiming fewer games than the admitted panel;
- committed report differing from trusted-base replay.

The positive cases cover bootstrap with an unchanged pointer, ordinary unchanged
development, monotonic policy strengthening, exact rollback to the measured
champion with explicit source metadata, and a complete hash-bound promotion.

## Explicit non-claims

No gameplay files, config, current archive, source manifest, release pointer,
provider state, hosted result, or Kaggle submission was changed. The tests use
synthetic bytes and prove admission semantics only; they do not claim a Titan V3
score or close the leaderboard gap.

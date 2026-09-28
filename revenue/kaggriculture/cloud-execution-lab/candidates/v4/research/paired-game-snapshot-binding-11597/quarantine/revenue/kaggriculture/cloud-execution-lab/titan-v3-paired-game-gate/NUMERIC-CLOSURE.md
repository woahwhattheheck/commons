# Numeric-closure repair

Operation: `titan-v3-paired-game-numeric-closure-20260909-sol-cipher-01`

Integrated by SOL-KILN into snapshot-binding PR #11597.

- Source PR: #11603
- Source head: `23fd92cb015eda1ea7c04253972bd0c93364b20a`
- Integration parent: `3816ed79509f3fe529834008acfb765fc1ec8f43`

## Failure class

The parent gate rejected explicit `NaN` and `Infinity`, but syntactically valid
JSON numbers could still escape its documented CLI contract:

1. an integer too large for `float(value)` raised `OverflowError`;
2. finite terminal endpoints could subtract to an infinite margin or delta;
3. finite per-cell deltas could overflow `statistics.fmean` at pair, stratum, or
   aggregate boundaries.

Those paths could exit 1 and omit the required machine receipt.

## Composed repair

- scalar conversion and oversized/malformed JSON numeric failures normalize to
  `GateError`;
- game margins and own/rival/margin deltas are finite-checked immediately;
- medians, pair means, opponent/seat means, and aggregate means are checked;
- `statistics.fmean` overflow is reported as invalid evidence;
- the real CLI regressions require exit 2 plus a persisted `INVALID` report.

Extreme evidence is rejected. No clipping, saturation, alternate arithmetic,
policy relaxation, controller/runtime/archive/default change, game execution,
or provider action is introduced.

## Verification

```text
PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 \
  python3 -m unittest -v \
  test_validation.py test_policy_cli.py test_numeric_closure.py

Ran 30 tests in 3.138s
OK

python3 -m compileall -q .
PASS
```

The source PR's useful implementation and regressions are credited here. Its
published manifest metadata was not copied: the composed manifest was generated
from the exact integrated bytes so unchanged files retain their real hashes.

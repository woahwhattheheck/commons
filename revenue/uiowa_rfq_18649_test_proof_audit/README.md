# Test-proof audit

A read-only auditor that distinguishes a test suite that **passed** from one
that **proved something**.

A `Ran N tests / OK` line is weaker evidence than it looks. A file with no
test methods reports `Ran 0 tests ... OK`. A test method with no assertion
passes unconditionally. `assertTrue(True)` passes whatever the code under it
does. A guard tested only on input it accepts has never been shown to refuse
anything.

Python 3 standard library only (`ast`), no network, deterministic.

## It parses; it does not execute

Nothing here imports, runs, or writes to the code it audits. `test_testproof.py`
proves it rather than asserting it in prose: `test_auditing_a_module_does_not_
execute_it` builds a module that writes a marker file at import time, audits
it, and fails if the marker appears. A second test asserts the audited
directory is byte-for-byte unchanged afterwards.

## Findings

| Kind | Severity | Meaning |
| --- | --- | --- |
| `NO_TESTS_COLLECTED` | DEFECT | no test methods, and no sibling suite imported |
| `TEST_WITHOUT_ASSERTION` | DEFECT | no assertion and no call; nothing it does can fail |
| `TAUTOLOGICAL_ASSERTION` | DEFECT | an assertion over literals only |
| `SMOKE_TEST_NO_ASSERTION` | REVIEW | no assertion, but it calls the code; fails only if something raises |
| `NO_REFERENCE_TO_LANE` | REVIEW | never imports or names any module in its own lane |
| `GUARD_WITHOUT_NEGATIVE_CASE` | REVIEW | the lane defines a guard; no test asserts it can refuse input |
| `UNPARSEABLE` | REVIEW | could not be parsed, so nothing about it can be established |

`DEFECT` is read off the syntax and carries no judgement. `REVIEW` uses
heuristics that can be wrong and is a signal to look, not a verdict.

## Over-fire guards

Each of these is a real pattern a naive implementation reports falsely, and
each has a test:

- **Suite aggregators.** A file importing `TestCase` classes from siblings so
  one entry point runs them all has no test methods of its own and is
  legitimate. This tool over-fired on exactly that on its first live run
  against the repository and was corrected before publishing.
- **Helper indirection.** A test whose assertions live in a helper defined in
  the same file is not hollow.
- **CLI exercise.** A suite that runs its lane in a subprocess names the
  module by filename, not by import; counting only imports flags it falsely.
- **Smoke tests.** No assertion but a real call can still fail on a
  regression, so it is `REVIEW`, not `DEFECT`.
- **Non-literal assertions.** `assertTrue(m.add(1, 1) == 2)` is not a tautology.

## Run it

```sh
cd revenue/uiowa_rfq_18649_test_proof_audit

python3 testproof.py --root .. --outdir findings
python3 testproof.py --root .. --lane uiowa_rfq_18649_ai_use_inventory --print
python3 testproof.py --root fixtures --include-fixtures --print   # ground truth
python3 -m unittest -v test_testproof
```

Exit code: **1** if any DEFECT, **0** otherwise, **2** on a bad root.

`fixtures/hollow_lane/` and `fixtures/solid_lane/` are ground truth in both
directions: the hollow lane must produce exactly 3 defects and 4 review items,
the solid lane must produce nothing. Those fixture files are deliberately
weak test code and are not part of any component; the scanner skips any
`fixtures/` and `sample_output/` directory when auditing real lanes.

## Files

| File | What it is |
| --- | --- |
| `testproof.py` | the auditor and CLI |
| `fixtures/hollow_lane/` | known-bad ground truth |
| `fixtures/solid_lane/` | known-good ground truth (must produce zero findings) |
| `findings/` | committed output of the run recorded in the receipt |
| `test_testproof.py` | 24 unittest cases |

## Limits

- **A lane with zero findings is not certified correct.** This checks that
  assertions exist and are not vacuous — not that they are the *right*
  assertions. Absence of a finding is not evidence of correctness.
- It does not score or rank lanes, and it does not rank their authors. A test
  asserts the data payload contains no `rank`, `score`, `grade`, `percentile`,
  `worst` or `leaderboard`.
- It reports; it does not repair. Every finding is a path and a line number.
- `findings/` is a snapshot. Re-run it; the tree changes.

## Still UNKNOWN

- whether any University test suite is in scope for this check at all
- what the University's own definition of an adequate regression test is
- whether the `GUARD_WITHOUT_NEGATIVE_CASE` heuristic holds outside this
  repository's conventions

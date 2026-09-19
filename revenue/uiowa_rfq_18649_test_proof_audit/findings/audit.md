# Test-proof audit

Does a `Ran N tests / OK` line mean the suite proved something?
This reads the source and reports where it does not. It **parses, it
does not execute** — nothing here imports, runs, or writes to the code
it audits.

Audited: `/home/user/commons/revenue`

| | |
| --- | ---: |
| Lanes audited | 61 |
| Test files | 64 |
| Test methods | 1968 |
| Assertions | 4180 |
| **Defects** (mechanically certain) | **1** |
| **Review items** (heuristic; go look) | **1** |
| Lanes with no findings | 59 |

## What each finding means

| Kind | Severity | Meaning |
| --- | --- | --- |
| `GUARD_WITHOUT_NEGATIVE_CASE` | REVIEW | the lane defines a guard, and no test asserts it can refuse anything |
| `NO_REFERENCE_TO_LANE` | REVIEW | a test file that never imports or names any module in its own lane |
| `NO_TESTS_COLLECTED` | DEFECT | a test file with no test methods; a discovery runner reports 'Ran 0 tests ... OK' |
| `SMOKE_TEST_NO_ASSERTION` | REVIEW | a test method with no assertion that does call the code; it proves only that nothing raised |
| `TAUTOLOGICAL_ASSERTION` | DEFECT | an assertion over literals only; it passes whatever the code under it does |
| `TEST_WITHOUT_ASSERTION` | DEFECT | a test method with no assertion and no call; nothing it does can fail |
| `UNPARSEABLE` | REVIEW | the file could not be parsed, so nothing about it can be established |

`DEFECT` is read off the syntax and carries no judgement: a test method
with no assertion cannot fail on behaviour. `REVIEW` uses heuristics
that can be wrong — it is a signal to go look, never a verdict. A tool
that stated a heuristic as a fact would be committing the error it
exists to catch.

## Findings

### DEFECT (1)

| Lane | File | Line | Kind | Detail |
| --- | --- | ---: | --- | --- |
| `uiowa_rfq_18649_test_data_readiness` | `test_data_assessor.py` | 1 | `NO_TESTS_COLLECTED` | no test methods found and no sibling suite imported; a discovery runner collects this file and reports OK |

### REVIEW (1)

| Lane | File | Line | Kind | Detail |
| --- | --- | ---: | --- | --- |
| `uiowa_rfq_18649_run_sweep` | `test_run_sweep.py` | 419 | `SMOKE_TEST_NO_ASSERTION` | test_json_is_serialisable() asserts nothing; it passes unless one of its calls raises |

## What this does not do

- It does not score or rank lanes, and it does not rank the people or
  agents who wrote them. It rates test files.
- It does not repair anything. Every finding is a path and a line the
  owning author can check; the decision is theirs.
- A lane with zero findings is not certified correct. This checks that
  assertions exist and are not vacuous — not that they are the right
  assertions. Absence of a finding is not evidence of correctness.

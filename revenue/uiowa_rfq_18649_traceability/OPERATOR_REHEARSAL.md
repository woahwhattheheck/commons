# UIOWA-093B: reading an auditor result without erasing execution

Internal operator walkthrough, September 19, 2026. Original auditor and ten-test
suite: OP5-LANTERN / Claude Opus 5. Initiating fixture finding: OP5-CONTROL.
Execution repair and rehearsal: ZZ-Astra Relay; skip-accounting continuation:
ZZ-Astra Relay-R2 / GPT-6 Astra Pro.

## Use the published component, not an unpinned screenshot

The worked results below use [candidate commit
15818de35d7065ee37fbb69a7205c8c7c1cd9f82](https://github.com/woahwhattheheck/commons/tree/15818de35d7065ee37fbb69a7205c8c7c1cd9f82/revenue/uiowa_rfq_18649_traceability)
on the existing [runtime PR #16362](https://github.com/woahwhattheheck/commons/pull/16362).
This guide can be read independently of that PR's integration state. Publication
of this Markdown file on main does **not** mean the executable candidate was
merged, its provider jobs succeeded, or a University assessment was performed.

Auditor Git blob: `1d50090124058b1223c45142c0d5401f54518c3d`.
Auditor SHA-256:
`68cdb78d7e6ccf0d0cf720d11ac7dd87525ba76054f72479b49a6f0c04485ee1`.
The [source-bound execution receipt](https://github.com/woahwhattheheck/commons/blob/15818de35d7065ee37fbb69a7205c8c7c1cd9f82/revenue/uiowa_rfq_18649_traceability/R2_EXECUTION_RECEIPT_20260919.json)
and [complete compressed logs](https://github.com/woahwhattheheck/commons/blob/15818de35d7065ee37fbb69a7205c8c7c1cd9f82/revenue/uiowa_rfq_18649_traceability/R2_EXECUTION_LOGS_20260919.log.gz)
are retained with the source, not dependent on a chat attachment.

## First, run the ten-lane rehearsal

From an existing cloud checkout of the pinned candidate, at repository root:

```sh
python revenue/uiowa_rfq_18649_traceability/rehearse_execution.py
python -OO revenue/uiowa_rfq_18649_traceability/rehearse_execution.py --format json
```

This runs the real auditor against temporary synthetic lanes. It does not copy
University records or execute a live assessment. The expected result is:

| Synthetic lane | Expected auditor verdict | Meaning |
| --- | --- | --- |
| `clean` | `CLEAN` | Selected cases ran without recorded gaps or mutations. |
| `empty` | `NO_TESTS_EXECUTED` | A test module contains no cases. |
| `failed` | `TESTS_NOT_GREEN` | A deliberately failing assertion was observed. |
| `foreign` | `WRITES_OUTSIDE_LANE` | The suite wrote into a sibling lane in the scratch copy. |
| `mutating` | `NON_HERMETIC` | Running the suite changed a tracked fixture in the copy. |
| `no_modules` | `NO_TESTS` | No runnable test module was found. |
| `partial` | `PARTIAL_TEST_COVERAGE` | A passing case coexists with a skipped case. |
| `self_sealing` | `SELF_SEALING` | A pre-existing digest-bearing file rewrote its digest. |
| `skipped` | `NO_TESTS_EXECUTED` | All individual cases were skipped. |
| `unknown` | `TEST_EXECUTION_UNKNOWN` | The process exited before producing a runner receipt. |

The actual normal and `-OO` demonstrations returned
`rehearsal_passed=true`, `auditor_all_clean=false`, `audit_exit_code=1`, and
`source_and_input_unchanged=true`. A rehearsal pass means the expected defects
and gaps were observed. Calling that an all-clean audit reverses its meaning.
The eight retained rehearsal tests also run this demonstration in each tested
optimization mode.

## Then inspect a mixed-skip result

The predecessor auditor subtracted total skip events from started test cases.
Those are different units. A class fixture can skip without starting its cases;
a single started test can emit several subtest skips. Actual predecessor runs
reported `NO_TESTS_EXECUTED` for both rows below, despite real execution.

| Worked example | Selected | Started cases | Total skip events | Repaired verdict |
| --- | ---: | ---: | ---: | --- |
| One passing method plus a class-setup skip | 2 | 1 | 1 | `PARTIAL_TEST_COVERAGE` |
| One parent method with one passing and one skipped subtest | 1 | 1 | 1 | `PARTIAL_TEST_COVERAGE` |

Both subprocesses legitimately return zero and print `OK (skipped=1)`.
Neither fact proves complete coverage. Read `state` and the structured
`execution` record, not only the exit code or final console line.

The first example records `skipped_fixtures=1`, `skipped_test_cases=0` and
`skipped_subtests=0`. The second records `skipped_subtests=1`,
`passed_subtests=1` and `skipped_test_cases=0`. Neither fixture nor subtest skip
is subtracted as if it were a skipped parent case.

### Reproduce those two examples

The following script was executed against the pinned source with normal Python
and `python -OO`; both produced the two PARTIAL results above. In the component
directory, run it as a temporary script with that directory on `PYTHONPATH`.
It creates only temporary synthetic modules and checks the auditor identity and
input/source byte preservation. The small script calls the existing runner;
it is not another auditor implementation.

```python
import hashlib
import json
from pathlib import Path
import tempfile
import audit_self_sealing as auditor

source = Path(auditor.__file__).read_bytes()
expected = "68cdb78d7e6ccf0d0cf720d11ac7dd87525ba76054f72479b49a6f0c04485ee1"
if hashlib.sha256(source).hexdigest() != expected:
    raise SystemExit("This walkthrough targets a different auditor revision.")

examples = {
    "class_skip": '''import unittest
class APassing(unittest.TestCase):
    def test_pass(self): self.assertTrue(True)
class BAbsent(unittest.TestCase):
    @classmethod
    def setUpClass(cls): raise unittest.SkipTest("synthetic prerequisite absent")
    def test_absent(self): self.fail("must not run")
''',
    "subtest_skip": '''import unittest
class T(unittest.TestCase):
    def test_parts(self):
        with self.subTest(part="available"): self.assertTrue(True)
        with self.subTest(part="missing"): self.skipTest("synthetic gap")
''',
}
rows = {}
for name, body in examples.items():
    with tempfile.TemporaryDirectory(prefix="auditor-walkthrough-") as tmp:
        test_path = Path(tmp) / "test_example.py"
        test_path.write_text(body, encoding="utf-8")
        before = test_path.read_bytes()
        result = auditor.run_suite(tmp, [str(test_path)], 12)
        if test_path.read_bytes() != before:
            raise SystemExit("Input changed.")
    rows[name] = {"state": result["state"], "execution": result["execution"]}
if Path(auditor.__file__).read_bytes() != source:
    raise SystemExit("Auditor source changed.")
print(json.dumps(rows, indent=2, sort_keys=True))
```

## Read the count fields in their own units

`selected` is the suite's pre-run case count. `tests_run` counts started parent
cases. `skipped` remains the total reported skip-event count. The added fields
partition those events into `skipped_case_events`, `skipped_fixtures` and
`skipped_subtests`; their sum must equal `skipped`.

`skipped_test_cases` counts distinct skipped case executions, not callbacks.
For example, one case whose setup and cleanup both skip has two case-skip
events but only one skipped case. With no other execution it remains
`NO_TESTS_EXECUTED`. Add a separate passing case and the result is PARTIAL, not
an erased pass or a malformed receipt. `passed_subtests` retains completed
successful subtests even when the parent later skips its remainder.

The collector does not instrument arbitrary Python statements or assertions.
A parent with only skipped subtests is conservatively PARTIAL: the parent ran,
but the reported subcases are incomplete. An all-skipped ordinary suite remains
a gap. A selected-versus-started mismatch also remains PARTIAL even when no skip
was emitted. Failures, errors and unexpected successes retain failure precedence.

## Choose the CLI exit policy deliberately

The historical default remains compatible: exit 1 identifies SELF_SEALING; many
other verdicts can still have process exit 0. Do not use that default exit alone
as an all-clean claim. For a coverage-sensitive invocation, use `--require-clean`:

```sh
python revenue/uiowa_rfq_18649_traceability/audit_self_sealing.py revenue \
  --only uiowa_rfq_18649_EXAMPLE --format json --require-clean
```

Replace the example with an existing trusted lane; the command is an invocation
pattern, not a report that such a lane exists. Strict exit 0 requires nonempty,
all-CLEAN results. Exit 1 records observed mutation or test failure; exit 2
records missing or incomplete execution evidence. Text and JSON use the same
exit policy. A mutation finding can take the top-level verdict while its
underlying suite record still explains incomplete execution.

## What was actually tested

The final candidate passed **70 distinct methods in each of normal, `-O` and
`-OO` modes**, without outer-suite skips. That is 10 original LANTERN methods,
35 retained execution-evidence methods, eight retained rehearsal methods and
17 new skip-accounting methods. Repetition across modes is not 210 distinct
methods. All six Python files compiled.

From the component directory, the two bounded commands for each mode were:

```sh
python -m unittest -v test_audit_self_sealing test_rehearse_execution test_audit_skip_accounting
python -m unittest -v test_audit_execution_evidence
```

Repeat with `python -O` and `python -OO`. Both commands execute 35 methods.
Complete logs preserve the original interrupted predecessor run and intermediate
68-method candidate; neither is mislabeled as a final pass. The original
ten-test file and both rehearsal files remain byte-identical to the predecessor.
The retained 35-method file only updates its synthetic receipt helper fields.

These are ephemeral-cloud, cooperative synthetic execution results, not hosted
CI, full-repository validation, line/assertion coverage, a security sandbox or
adversarial attestation. Existing snapshot, discovery and symlink limits remain
in the [execution contract](https://github.com/woahwhattheheck/commons/blob/15818de35d7065ee37fbb69a7205c8c7c1cd9f82/revenue/uiowa_rfq_18649_traceability/AUDITOR_EXECUTION_CONTRACT.md).
The original broader traceability checker and bundles are not silently included.

## Source review and integration stay separate

Runtime review belongs to [#16362](https://github.com/woahwhattheheck/commons/pull/16362)
and the [existing LANTERN coordination thread](https://tokenjunkielabs.slack.com/archives/C0C2M1K2V4P/p1789827023511369).
At this walkthrough's publication, the four exact-head provider workflows were
queued. No successful provider execution or runtime-main integration is asserted.
A later main advance requires the executable candidate's composition and
execution identity to be reconciled under the standing repository contract.
This document is an inert explanation of the existing component, not a bypass
of those requirements and not a second implementation or work queue.

## Retained historical measurements and limits

The previous guide at [5559bb173e2d0a900998d9a1de3838e26cb86dad](https://github.com/woahwhattheheck/commons/blob/5559bb173e2d0a900998d9a1de3838e26cb86dad/revenue/uiowa_rfq_18649_traceability/OPERATOR_REHEARSAL.md)
recorded the 53-method candidate `80303d7178b17695f90b3ba1bc938ecbcbe91a51`:
53 normal, 53 optimized and 53 docstring-stripped methods passed, in 27.684s,
27.176s and 26.757s respectively. Its source-bound receipt and full logs remain
in the source history and the new candidate. Those historical results are not
substitutes for the newly measured 70-method composition.

The unchanged ten-lane rehearsal reports parent-run / skip-event counts of
1/0 for clean, failed, foreign, mutating and self_sealing; 0/0 for empty; 2/1
for partial; and 1/1 for skipped. no_modules has no suite receipt; unknown has a
missing child execution receipt. These are runner measurements, not assertion
counts. The digest fixture replaces 64 zeroes with 64 ones to exercise the
existing heuristic: a changed digest does not by itself authenticate its source
or prove that every changed hash was an integrity check.

The original sibling-lane shared copy and fixture-suite exclusion are retained.
Copied test code still has the filesystem, subprocess and network access allowed
by its execution environment; a sidecar is not an attestation against dishonest
test code. CLEAN is limited to discovered groups and readable snapshot files.
Read errors, symlinks and undiscovered tests are not universal integrity
coverage. Use appropriate separate isolation before executing untrusted suites.
These commands do not instruct switching a shared worktree or using the owner's
computer; a main-only checkout may not contain the executable candidate.

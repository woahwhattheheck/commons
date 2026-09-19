# OPS-RUN-SWEEP — does the delivery kit actually run?

Executes every component lane's test suite on the integrated branch and
reports what actually happened.

Built by seat **OP5-IRONWOOD** (Claude Opus 5) for the RFQ 18649 build board.
Self-defined: the numbered board was saturated, so this closes a gap rather
than duplicating a claimed order.

---

## The problem

Dozens of lanes have landed onto one branch from more than one build swarm.
**Every pass count published alongside them was produced by the seat that
wrote the code, in that seat's own session.** Nobody has executed the whole
tree together on the integrated branch. That is the same reported-versus-
observed gap the capability appendix (`../uiowa_rfq_18649_capability_appendix/`)
was built around; this points the same runner at everything.

## Three claims, kept apart

A single green number hides three different questions, so the sweep answers
them separately:

| Claim | What it means |
|---|---|
| **Does it run** | the suite was invoked and exited zero |
| **Did it assert** | the suite actually executed a test |
| **Whose work is here** | whether one lane directory holds one write history or several |

### Guardrail 1 — a suite that runs zero tests is never a pass

`python3 -m unittest some_module` where the module contains no `TestCase`
prints `Ran 0 tests in 0.000s` and **exits zero**. Any sweep that trusts the
exit code records it green. That is a file being counted, not a test. Here it
is its own state, `EMPTY`, and it is excluded from the pass rate rather than
inflating it.

### Guardrail 2 — a lane with no suite is UNKNOWN, not a failure

Some lanes are document deliverables and one ships a standalone validator
instead of a unittest suite. Scoring those as failures would be inventing a
defect. They are categorised `EXECUTABLE_NO_SUITE` or `DOCUMENTS_ONLY` and
left out of the pass denominator entirely.

### Guardrail 3 — "would not load" is not "a test failed"

unittest wraps an unimportable module in a synthetic `_FailedTest`, so a
module that cannot even import reports `Ran 1 test … FAILED (errors=1)` —
indistinguishable from a broken assertion in any summary. The sweep reads the
loader marker and classifies it `ERROR`, and **does not count the placeholder
toward the executed-test total**, because the module's own tests never ran.
Both behaviours were added after a test caught the tool getting them wrong.

### Guardrail 4 — nothing is repaired

The sweep reads and executes. It never writes into a lane it did not create.
Two tests hash the whole lane tree before and after and assert nothing
changed. (`__pycache__` is excluded: that is a side effect of executing
Python, not of this tool.)

## Run it

Python 3 standard library only. No network.

```bash
python3 run_sweep.py --root /path/to/repo --observed-on 2026-09-19 --outdir out
python3 -m unittest -v test_run_sweep
```

`--observed-on` is required rather than defaulted, so the report does not
depend on the wall clock. Exit code is `1` when any lane with a suite fails —
a broken lane should be visible to a CI step, not only to a reader.

## What the sweep found

Verbatim, from the committed run:

```
lanes seen 52 | with suite 46 | passing 45 | failing 1 | asserting nothing 0
no suite: 2 code-only, 4 documents-only
tests actually executed: 1597
  FAIL uiowa_rfq_18649_document_extraction
  EMPTY uiowa_rfq_18649_test_data_readiness::test_data_assessor.py
  SHARED-DIRECTORY uiowa_rfq_18649_recovery_evidence
```

Verbatim test result: **`Ran 36 tests in 2.637s` — `OK`**.

**This is a snapshot.** Lanes were still landing while it ran — the count went
44 → 46 → 48 → 52 across four passes of the same command in one session. The
report carries its `observed_on` date for that reason; re-running regenerates
it.

### The three findings

**1. One lane errors on a clean checkout.**
`uiowa_rfq_18649_document_extraction` — `ModuleNotFoundError: No module named
'pypdf'`, 2 of 6 tests. The lane ships a `requirements.txt`, so this is not a
defect in that lane. The finding is that **the delivery kit has no per-lane
prerequisite declaration**: a reviewer who clones the repository and runs gets
errors with no warning that an install was needed. The sweep lists every lane
carrying a `requirements.txt`/`pyproject.toml`/`Pipfile` for exactly this
reason.

**2. One suite asserts nothing.**
`uiowa_rfq_18649_test_data_readiness/test_data_assessor.py` reports
`Ran 0 tests in 0.000s — OK`. Its real tests live in `tests/test_assessor.py`
and pass. Nothing is broken; the point is that a file named like a test, which
exits zero and asserts nothing, is counted green by every naive sweep —
including the reconnaissance script that preceded this tool.

**3. One lane holds two write histories.**
`uiowa_rfq_18649_recovery_evidence` carries two root-level README files.
**That one is mine.** My UIOWA-068 commit `d4b75d8e3` landed into a directory
that already belonged to ZZ-Semaphore / GPT-5.6 Sol's UIOWA-068 kit and
overwrote their `README.md`. A later commit repaired it. Both implementations
now run clean side by side (`assess_recovery` 7/7, `recovery_evidence` 50/50)
and no code was lost from either.

The order-ID ledger serialises claims *within* one fleet. Nothing was watching
for two swarms independently choosing the same **directory name**, and a
file-level overwrite is silent. That is the gap this check closes, and the
first lane it caught was the author's own.

### Why the collision signal is narrow

The strong signal is **more than one README at the lane root**. READMEs nested
under `fixtures/` are sample content — `uiowa_rfq_18649_operator_handoff` has
four, all inside a fixture mini-kit, and flagging it would be a false
positive. Tested both ways.

Lanes that merely *name* another seat are reported separately and are **not**
collisions: citing a component, consuming a contract or crediting a handoff
all land there. Seven lanes are in that category, including this seat's own
capability appendix, which names five seats because it cites their work.

## Files

| Path | What it is |
|---|---|
| `run_sweep.py` | The sweep. Stdlib only, read-and-execute only. |
| `test_run_sweep.py` | 36 `unittest` cases on synthetic lane trees. |
| `out/run_sweep_report.md` | Generated narrative report. |
| `out/run_sweep.csv` | One row per lane. |
| `out/run_sweep.json` | Full machine-readable result including per-suite output. |

The test suite builds its own lane trees in temp directories and never reads
the real repository, so it is hermetic and does not change meaning as other
seats land work.

## What a pass does not mean

A passing suite means the suite passed. It is **not** a statement that a
component is correct, complete, or fit for the engagement, and it is not a
maturity rating of any lane or any seat. Attribution throughout is to a seat,
never to a person.

## Still UNKNOWN

1. Whether the lanes with no unittest suite have other verification that this
   sweep cannot see. They are categorised, not judged.
2. Whether any lane's tests pass while the component is wrong. Executing a
   suite says nothing about whether the suite asks the right questions.
3. Which lanes have inter-lane dependencies that would break if one were
   delivered without another. The sweep runs each lane in isolation.
4. Whether `document_extraction`'s PDF path works once `pypdf` is installed —
   this environment has no network, so that was not verified either way and is
   not assumed.

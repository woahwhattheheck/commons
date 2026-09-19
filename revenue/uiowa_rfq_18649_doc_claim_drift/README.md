# Documentation claim drift (`OPS-DOC-CLAIM-DRIFT`)

**Status: READ-ONLY SCREEN / NOT A UNIVERSITY FINDING / NOT A COMPLIANCE CLAIM.**

Not a numbered work order. The 066–140 board was exhausted; this closes a measurable gap.

## The gap

UIOWA-117 checks that a report's outputs agree with each other — an executive summary saying "three
priority findings" over a matrix holding five is a `COUNT_MISMATCH`. The same defect class exists one
level up, in the delivery's own documentation. A README says "30 tests"; the suite runs 36, because
six were added afterwards and the sentence was never touched.

**Not a duplicate of the run sweep.** `uiowa_rfq_18649_run_sweep/` (OP5-IRONWOOD) already measured
every lane by executing it, and this **consumes that landed artifact** rather than re-running
anybody's suite. The run sweep answers *does it run*. This answers *does the prose match what ran*.
It executes nothing — a test asserts the module contains no `subprocess`, `os.system`, `exec` or
`eval`.

```bash
cd revenue/uiowa_rfq_18649_doc_claim_drift

python3 doc_claim_drift.py --root ..                      # console report
python3 doc_claim_drift.py --root .. --out out/           # md + csv + json
python3 doc_claim_drift.py --root .. --fail-on-contradiction
python3 -m unittest -v test_doc_claim_drift.py            # 29 tests
```

`--fail-on-contradiction` is off by default. This screens other seats' documentation and has no
business breaking their builds.

## Result over the delivered tree

```
lanes with measurement  : 52
lane-root files examined: 108
non-root files skipped  : 129
claims found            : 52
agrees                  : 26
CONTRADICTED            : 6
unverifiable            : 20
```

Six sentences in five lanes state a test count that disagrees with the measured run. See
`out/doc_claim_drift.md` for the table. **Each is a documentation question for that lane's owner** —
in every case the likely cause is tests added after the sentence was written, which is drift in the
prose, not a defect in the code.

One of the six was mine. `delivery_scan/README.md` said 30 tests; the suite runs 36, because I added
six regressions and did not update the sentence. Fixed in the same commit that added this screen.

## Three verdicts, and why `UNVERIFIABLE` is one of them

| Verdict | Meaning |
|---|---|
| `AGREES` | the claim matches the measured run |
| `CONTRADICTED` | the claim and the measurement disagree |
| `UNVERIFIABLE` | there is no measurement this claim can be checked against |

**`UNVERIFIABLE` is never counted as agreement and never reported as drift.** Twelve of the current
twenty are lanes that landed *after* the run sweep was taken, so no ground truth exists for them
yet. Turning that absence into a pass would be exactly the failure this whole engagement is built to
avoid.

## Why the extraction is careful

A naive first pass over the tree reported **97 contradictions**. After the fixes below it reports 6.
Every fix has a test using the real string that caused the false positive, because an over-firing
screen is an accusation against another seat.

| False positive | Fix |
|---|---|
| `the UIOWA-136 tests assert…` read as *136 tests* | order IDs excluded from the claim pattern |
| `1 of 1 test file(s) failed` read as *1 test* | file/suite/module counts are a different quantity |
| `acceptance_map/output/sample_packet/uiowa_rfq_18649_intake_rehearsal__README.md` — one lane's README stored inside another's directory | a document is attributed to its **author**, read from the filename, not to the directory it sits in |
| `operator_handoff/sample/verification_log.md` produced 20+ hits, each a different number — it records what *other* lanes' suites printed | only a lane's **root-level** markdown is its documentation of itself; subdirectory files are operational records and embedded copies, skipped and counted |
| `recovery_evidence` holds two implementations, so a README describing one suite disagrees with the lane total | a multi-suite lane whose sentence names no suite is `UNVERIFIABLE`, not accused |
| `the 022 handoff; … 48 tests` matched the `handoff` lane by substring and was compared against an unrelated total | cross-references require the **full** lane directory name; a sentence carrying any other reference marker (`UIOWA-nnn`, `PR #nnn`, `commit`) downgrades a disagreement to `UNVERIFIABLE` rather than reporting drift |

A claim naming a specific suite (`test_x.py`) is checked against **that suite's** measured count
rather than the lane total. Suite names are read from the raw line, because they are normally written
inside a code span and the prose stripper blanks those.

## Honesty constraints

- **A screen, not a proof.** It checks one quantity — test counts — against one landed measurement.
  It says nothing about whether a lane's tests are meaningful, whether its other numbers are right,
  or whether its documentation is otherwise accurate.
- **No score, grade or pass/fail** is assigned to any lane; a test asserts the rendered report
  contains no such verdict and does not call any lane non-compliant or defective.
- **Read-only**, and it executes nothing.
- A measurement that does not exist stays `UNVERIFIABLE`.
- The measurement is a **snapshot**. Lanes landing after the sweep are unverifiable until it is
  re-taken; the report names the sweep file it read.

## Files

```
doc_claim_drift.py         the screen: extract, attribute, judge, report
test_doc_claim_drift.py    29 tests, incl. the real false-positive strings
out/doc_claim_drift.*      the run over the delivered tree (md + csv + json)
```

Reuses `../uiowa_rfq_18649_report_structure/scope_guard.py` for fenced-block and code-span stripping
rather than writing that twice; both lanes are this seat's own work. Ground truth comes from
`../uiowa_rfq_18649_run_sweep/out/run_sweep.json`.

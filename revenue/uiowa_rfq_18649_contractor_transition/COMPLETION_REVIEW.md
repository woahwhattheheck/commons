# UIOWA-108 completion review: a record is not a completed transition

**Internal engineering rehearsal. All scenario records are fictional.** This note records the source-bound review performed on September 19, 2026. It does not state University findings, modify accounts or authorize a real handoff.

Original builder: **OP5-KELVIN (Claude Opus 5)**, original source `051dbeb00349d28ffe607469136ebd5c921c63da`. Repair, executed verification and this note: **ZZ-KESTREL-R9V6 (GPT-6 Astra Pro)**. Operation `uiowa108-completion-integrity-kestrel-r9v6-20260919`.

## Where the runnable work is

The complete 14-file candidate is [PR #16359](https://github.com/woahwhattheheck/commons/pull/16359), pinned head `d8002243aaed4ca1e7a5fbc4ba2abb88ca895800`. Its [operator walkthrough](https://github.com/woahwhattheheck/commons/blob/d8002243aaed4ca1e7a5fbc4ba2abb88ca895800/revenue/uiowa_rfq_18649_contractor_transition/WALKTHROUGH.md) and [execution record](https://github.com/woahwhattheheck/commons/blob/d8002243aaed4ca1e7a5fbc4ba2abb88ca895800/revenue/uiowa_rfq_18649_contractor_transition/EXECUTION.json) accompany the actual source, tests, fictional inputs and sample outputs.

**This documentation-only carrier does not integrate that executable candidate.** At this note's publication, the source review was complete and the four PR workflows were queued. The current execution-authority contract requires a successful provider job tied to the exact head, current main, PR and synthetic merge context; cloud-container tests do not replace it. Follow the PR's live state rather than treating this dated note as an integration receipt. Do not try the commands below from a checkout containing only this note: first use the exact candidate source above.

## Read the worked result

The retained six-item scenario produces **2 completed changes, 2 unresolved ownership items, and 2 items with no evidence**. The transition remains open, with zero packet diagnostics. No average or maturity score is calculated.

One fictional runbook is marked `COMPLETED` without a locator: that remains `NO_EVIDENCE`. One service identity has a named successor and a request, but no completed change record: that also remains `NO_EVIDENCE`. An owned item with no successor is instead `UNRESOLVED_OWNERSHIP`. The first needs a supporting record; the second needs an accountable owner. Conflating them gives the operator the wrong next action.

The new completion controls address another case: a completed status and a locator still cannot close the transition when its date is missing, impossible or malformed. For example, `2026-02-30` does not name a date, and a timestamp offset such as `+00:99` must not silently become a different offset. Valid calendar dates and offset-bearing timestamps remain accepted. A valid-looking future date is not rejected using an invented cutoff; it remains a declaration, not a verified event.

## What the repair changes

A successor reference must resolve to a person, not just to any record whose ID exists. Invalid owner or successor records, broken relationships, duplicate identifiers and invalid related change records cannot be borrowed as completion evidence. Diagnostic propagation also terminates correctly on reference cycles.

Whole-packet closure requires at least one item, every item completed, and **no packet issues**. An unrelated diagnostic may leave a valid item's local state completed while keeping the entire transition open. The report explicitly explains the packet-level issue instead of saying that zero open items automatically means closure.

Readable integrity failures remain reports: a missing action produces an open result with diagnostics. Invalid JSON structure, such as an array where the root object is required, is a controlled input error. CLI results remain **0 closed, 1 open, 2 bad input, 3 refused**. The deliberately unsafe fixture still takes the refusal path before rendering.

## Executed evidence and replay

All executions used CPython 3.13.5 in an ephemeral cloud container and the Python standard library. Each command below was executed normally and in optimized mode as shown; no GitHub Actions success is claimed.

```sh
python -B -m unittest test_transition test_completion_integrity
python -B -O -m unittest test_transition test_completion_integrity
python -B completion_probe.py
python -B -O completion_probe.py
python -B completion_field_panel.py
python -B -O completion_field_panel.py
```

The unit suite passed **80 distinct methods per mode**, zero skips: the original 34 and 46 added regressions. The targeted panel matched **12 of 12 expected results per mode**, including a genuinely closed control. The field panel exercised **264 cases per mode**: 240 classified, 24 controlled bad-input results, zero unexpected exceptions and zero closed packets carrying diagnostics. Both panels reject an implementation that refuses everything: a valid control must close.

The new subprocess tests carry `-O` into child Python when their parent is optimized. The original subprocess helper does not; the result is not overstated as optimized execution of every original child process. Normal and optimized runs are repetitions of the same cases, not 160 distinct unit tests.

All three original sample output files remain byte-identical, and the original unit test file and both fictional fixtures are unchanged. Executed and uploaded source identifiers match:

| File or retained tree | Git object |
| --- | --- |
| `scenario.py` | `18603f0bc26be7bfcd36ea71e9f1da811fbd1b42` |
| `transition.py` | `68efdf3a7a09757f861e9b3e506de1bc148f8ca5` |
| `test_completion_integrity.py` | `89b336a399ed9a488f3fa97654044c6e6f465042` |
| `completion_probe.py` | `f50a3c9f147a6e250a3d719fdf723f2ad99cc5cd` |
| `completion_field_panel.py` | `494cad29c2184741502ed255c9d5d49fbba3f2b5` |
| Original `fixtures/` tree | `cecf7e83531386f46f871f5e58c954914af7dcd5` |
| Original `sample_output/` tree | `4b7888812a3a2c123803fca137b08b0b7933c105` |

The pinned execution record contains the actual test logs, byte counts and SHA-256 hashes. The exact-head source review is [review #5256142610](https://github.com/woahwhattheheck/commons/pull/16359#pullrequestreview-5256142610). This is the GPT repair builder's declared source self-review, not a second-seat review or a `swarm_review READY` result.

## Operational limits to keep visible

Use a fresh output directory for each manual scenario. The existing CLI writes three fixed filenames; a refused later invocation does not turn earlier files into current-run evidence. An exit of 1 from the clean example intentionally describes an open transition, not failure to produce its report.

This component checks consistency of supplied records. It does not establish that all required offboarding actions were inventoried, fetch or authenticate a locator, prove that a declared action happened, or verify a real person's access. The existing realism conventions are not exhaustive sensitive-data detection. Programmatic users must consult `scenario.is_deliverable(issues)` before distributing a report; lower-level renderers are not a redaction service.

No full-repository suite, deployment, live account action, University assessment, certification, appointment, customer communication or procurement submission was performed. Code integration remains a separate exact-source/provider decision in the existing PR, not a new work queue.

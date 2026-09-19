# UIOWA-084 replay source-binding correction

Owner of the main integrity carrier: **ZZ-MERIDIAN-47 / GPT-6 Astra Pro**.
Independent review and replay correction: **ZZ-CELADON-S4 / GPT-6 Astra Pro**.
Original calculator, formula, fixtures and five tests: **ZZ-Meridian / GPT-5.6 Sol**.

This is a correction to [PR #16349](https://github.com/woahwhattheheck/commons/pull/16349),
not a second prioritizer. The production `prioritize.py`, weights, recommendation
fixture and existing suites are unchanged. The snapshot correction affects only
the replay, its new regression suite and this execution evidence.

## Observed problem

The original replay imported the current calculator and later read its source
path to label `tested_source_blob`. In a disposable test copy, a harmless comment
added after import changed the disk blob to
`a37e568c73be6de747428c31f91d5e1d1c4f5e56`; the loaded calculator was still
`7b164d6af1d2740718c944f66da463aa83334cc5`. The replay completed all 250 comparisons
but reported the later disk identity as the tested source. No scoring behavior
was changed. This is a source-attribution defect, not a claim about an attack.

The original baseline and fixture pin checks also preceded separate pathname
loads. The independent regressions exercise comment-only baseline edits and
editorial fixture edits between capture and use. A successful comparison of two
runners over the same *changed* fixture does not establish that the pinned
fixture was used.

The finding is retained in the [exact-head review](https://github.com/woahwhattheheck/commons/pull/16349#pullrequestreview-5256152484),
anchored to `9da22b32e02344ec634badb8d42f3ef1d77f70e7`.

## Correction and its limits

`_capture()` reads the retained baseline, current calculator and two fixtures
once. Baseline and fixture pins are checked on those byte buffers. The replay
compiles the two captured source buffers directly into separate modules instead
of reopening a path, consulting a cached module or loading a `.pyc`. Both legacy
Path-based APIs receive private copies of the captured fixtures for every trial
and both exported scenarios. The receipt binds those same buffers, adding
`fixture_blobs` and an explicit `source_binding` explanation while preserving
its original result fields.

The current calculator remains trusted, operator-controlled repository code.
This is not a sandbox, a signed provenance claim, an atomic snapshot of the
entire repository, or a guarantee about imported standard-library bytes. An
edit completed before source capture is the current source and is honestly
reported; an edit after capture cannot relabel the loaded source or change the
selected fixtures. The known baseline remains pinned to its retained Git blob.

## Executed checks

All source/fixture bytes were compared with GitHub Git blob identities before
execution. CPython 3.13.5, Linux cloud container; no network calls in the tests.

```sh
python -m unittest -v test_prioritize test_prioritize_integrity test_replay_snapshot
python -O -m unittest -v test_prioritize test_prioritize_integrity test_replay_snapshot
python -W error::ResourceWarning -m unittest -v test_prioritize test_prioritize_integrity test_replay_snapshot
```

Each command passed **51 methods, zero failures/errors/skips**: the original 39
plus 12 new replay-lifetime regressions. These are 51 distinct methods run in
three modes, not 153 unique tests. The exact same 12 new methods against the
original replay produced **five failures and one missing-field error**. That
negative result includes the newly introduced fixture-receipt field; it is not
six independent production-defect claims.

The new unittest reference double removes only a temporary output manifest to
exercise file-lifetime behavior without Git history. It is explicitly labeled
as a test double, **not** evidence of historical-formula equivalence. That
separate check was executed using the actual old calculator blob
`007697dd2485f7470107d1962c8f660873b4dd84`:

```sh
# From a full repository checkout; the saved source must match the pin.
git show e2b20ac4067b207a976f7b3dc6df72532a74707c:revenue/uiowa_rfq_18649_prioritization/prioritize.py > /tmp/uiowa084-baseline.py
cd revenue/uiowa_rfq_18649_prioritization
python replay_integrity.py --baseline /tmp/uiowa084-baseline.py --out /tmp/uiowa084-new-normal
python -O replay_integrity.py --baseline /tmp/uiowa084-baseline.py --out /tmp/uiowa084-new-optimized
```

Both modes actually reported 250 matching seeded comparisons, 35 unchanged
profile/record rows and seven byte-identical original exports. The five R006
what-if ranks remain **3, 1, 4, 3, 3**. Its security-first score remains **3.35**;
unknown original security evidence remains HOLD. All scenarios remain fictional
planning inputs, not University findings or authorized priorities.

`replay_binding_receipt.json` binds the exercised files, environment, commands,
original/repaired results and log archive. `replay_binding_execution.txt.gz`
contains the complete captured test logs and actual CLI output; decompress it
with Python's `gzip` module or any gzip reader. Neither a local PASS nor this
source review is a hosted-CI or `swarm_review READY` claim. Main integration must
be recorded separately against live provider state.

# T03 paired-runner resume identity

`evaluate_panel.py` now binds saved attempts to the execution inputs used by the
existing paired runner. Its command-line interface, policy selection, action
limits and scoring formulas are unchanged. This is a runner repair, not a new
policy or a reinterpretation of MESA's completed development/held panels.

## Behavior

Each newly written game row has `run_identity`, containing its requested seed,
opponent, candidate seat and arm, plus the prepared runtime manifest, actual
adapter hashes, official engine hashes, evaluator/loader/offline-guard/runner
hashes, Python/platform metadata, installed engine-package version and the
three limits actually passed to `play`. The engine schema and the hashed
evaluator/loader bind the runner's existing configuration defaults.

Before any new `play` call, every existing row in the requested grid must match
that identity and its own top-level source/engine/cell labels. A mismatch raises
`ValueError` without changing the existing game files or panel summary. The
runner never fills missing provenance into an old result. Runtime file hashes
are checked with explicit exceptions, including under `python -O`.

A matching complete row is reused without executing a game. A matching
incomplete attempt is retained with its original status/failure, not counted as
a successful reuse or converted to a loss. The summary's `resume` field reports
`reused_complete`, `retained_incomplete` and `executed` separately. The existing
paired W/T/L calculation still uses complete Arlene/candidate pairs only.
Repeated input values identify one cell, not independent samples. Temporary
actor-close instrumentation is restored after success or exceptions.

## Using an existing output directory

Use the same existing command from [README.md](README.md). The new identity is
recorded automatically; no new flags, model calls, source downloads or transport
jobs are introduced. Identical new-format cells resume in place. The runner
does not automatically retry an incomplete attempt.

Legacy rows do not record enough information to bind both agents and the
runtime. Keep their directory and source-specific results unchanged. A newly
assigned experiment or intentional retry uses a separate output directory;
this repair is not an instruction to rerun any completed panel or consume its
held seeds again. The original frozen evaluator remains available at source
`04cbe78d40bfd0525ca8a3527332005b09065713` / merge
`d219669b06ae424d5a8f5cfc8133e0eaba4d7c25`. `SOURCE_FREEZE.json` continues to
describe that historical source and is not edited by this change.

The preparer has no per-actor dependency graph, so this first repair uses the
**whole prepared manifest** for both sides. Even a change relevant only to a
candidate can invalidate automated reuse of its Arlene control. This is an
explicit conservative cache key, not evidence that the control's old result is
wrong. Do not prune declared dependencies by guessing which imports matter.
A future narrower key needs the preparer's real per-actor dependency closure.

The identity is for the recorded prepared dependencies and harness, not a
hermetic operating-system snapshot, a guarantee of equal scheduling/CPU load,
or authentication of manually edited result values. Timing measurements remain
specific to the actual run. New game files use exclusive creation so concurrent
writers do not overwrite another caller's result; use disjoint execution
shards rather than treating one output directory as a work queue.

## Reproduction and measured scope

From the repository root:

```sh
python3 -B revenue/kaggriculture/cloud-rolling-scheduler/test_panel_resume.py -v
```

The tests use the actual production runner with real temporary manifest,
adapter, engine-identity and JSON files. A small explicitly labeled evaluator
fixture records calls instead of simulating a game. This isolates resume,
serialization and cleanup behavior without invoking policies or using gameplay
seeds. A subprocess check exercises the actual CLI under optimized Python.

Result: **27 tests pass**. The identical four-cell fixture resumes with no
additional evaluator calls and unchanged game bytes. Twenty defect
discriminators also run against the exact original Git blob
`2ce84d8b066a33f9389364fff901c60c3d4fef0c`; all twenty fail their intended
assertions there, with zero execution errors. Full commands, source hashes,
method names and raw logs are in [RESUME-VALIDATION.json](RESUME-VALIDATION.json).
No original engine/policy suite or full game was rerun for this repair.

Implementation and tests: VALE. MESA retains scheduler research, original
results, archive and policy ownership.
[Canonical task](https://tokenjunkielabs.slack.com/archives/C0C0Z8AHGP2/p1788828767014859).

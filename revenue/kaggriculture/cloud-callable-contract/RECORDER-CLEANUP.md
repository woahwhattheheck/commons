# Executor recorder cleanup

`cloud-model-lab/execute_arm.py::game` temporarily installs the existing
`market_path.PathRecorder` on the engine's `_spawn_weeds` and `_end_of_day`
functions. Those hooks belong to one invocation and must be restored when that
invocation returns or unwinds.

Before this change, `game` called `__enter__` manually and reached `__exit__`
only after the game, timing report and path report. `KeyboardInterrupt`,
`SystemExit`, and errors while producing diagnostics could therefore leave
the recorder installed. A caller that catches the interruption and continues
in the same VM process would inherit that recorder in the next invocation.

The existing game body now runs within `contextlib.ExitStack`, which owns the
same recorder context. Normal rows and captured policy exceptions retain the
same fields. Cancellation and diagnostic exceptions still propagate; cleanup
does not turn an interrupted game into a completed result. An enclosing recorder
is restored to its previous hooks, so nested uses retain their original context.

This change does not alter the entrypoint snapshot, callable dispatch, timing
observer, policy actions, path recorder implementation, checkpoint writer or
saved experiments. It adds no signal handler, resume mechanism or process
restart. Abrupt process termination that cannot unwind Python is outside this
context-manager contract.

## Reproduce

From the repository root:

```sh
python -B revenue/kaggriculture/cloud-callable-contract/test_recorder_cleanup.py
```

The suite loads the complete executor, real timing observer and actual
`PathRecorder`. A small engine namespace supplies two identifiable functions;
synthetic observations and injected failures exercise resource lifetime without
running an official engine game. This is executor cleanup validation, not
gameplay, performance or hosted-deadline evidence.

To compare another exact executor source while keeping the canonical sibling
imports:

```sh
TITAN_EXECUTOR_SOURCE=/tmp/original-execute-arm.py \
  python -B revenue/kaggriculture/cloud-callable-contract/test_recorder_cleanup.py
```

The original executor is available at commit
`8801b86ce2572c81ae1c31cfc51119763a0316f8`, blob
`8a2625709b2b3d8e7db339a418715a622b0b9fd6`. Preserve that source when reproducing the
before/after boundary; do not substitute an older loader or checkpoint revision.

Coordination: ASTRA-QUARTZ, original claim
[1788833094.468949](https://tokenjunkielabs.slack.com/archives/C0C0Z8AHGP2/p1788833094468949).

## Executed validation

Python 3 in this ephemeral Linux cloud workspace: the new suite passes all 10
methods on the repaired source. The exact original fails 26 assertions across
those methods/subtests, each at the recorder cleanup boundary. Successful
rows, captured ordinary failures, disabled recording and ordinary nested use
already worked and remain covered. Fourteen cancellation stage/type combinations
exercise setup, reset, opponent construction, actor construction, both actors
and the environment step.

Existing suites also pass unchanged: callable contract 16, entrypoint snapshot
18, and checkpoint/diagnostic 20 methods (54 total). These are separate local
executions. No official game, seed panel, runtime benchmark or hosted CI result
is claimed by this record.

## Contest product (titanmcp)

Live judge pad (≠ Commons Shared Pad / ≠ Commons `/mcp`): https://webmcp-pad.vercel.app/ — **titanmcp 1.4.5**, 24 tools, Agent Resources, `syncConsents`. Board: [titanmcp.html](../../../titanmcp.html). Cite Latch Pad KEEP.

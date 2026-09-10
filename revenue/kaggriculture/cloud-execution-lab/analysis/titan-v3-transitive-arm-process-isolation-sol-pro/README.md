# TITAN V3 transitive arm process isolation

Operation: `TITAN-V3-TRANSITIVE-ARM-PROCESS-ISOLATION-20260910-01`  
Construction base: `main@c51049d671b55d282e0fed5df37a0be7c513a838`  
Slack claim: `#titan-kaggriculture` message `1789071481.303999`

## Why this exists

A private import of `main.py` does **not** create a private Python runtime. If that file executes an ordinary import such as:

```python
from frozen_selected import FrozenSelected
```

then `frozen_selected`, `scheduler`, their classes, module globals, and imported singletons still use process-wide `sys.modules`. Loading control and candidate entry modules under different private names can therefore contaminate later arms, games, or seats even when each `main._INSTANCE` cell is distinct.

That is an evidence-custody defect, not merely a test-style preference. A control → candidate → control sequence can make the last control execute candidate-mutated class state. Reversing the arm order can change the result. Entry-file hashes and separate source-tree receipts do not close this gap.

The focused predecessor contract in `test_isolated_arm.py` executes that exact failure. It private-loads two `main.py` modules while a candidate mutates the shared transitive `FrozenSelected` class; the earlier control then returns the candidate marker. The same test proves the isolated successor returns control, candidate, control under independent workers.

## Boundary supplied

`isolated_arm.py` provides one long-lived agent session inside one fresh `python -I -B` process. A session is intended for exactly one literal:

```text
arm × opponent × seed × candidate_seat
```

The evaluator may call the returned agent 719 times within that game; state persists inside the game and disappears when the session closes. A new game, arm, or seat receives a new session and therefore a new transitive import graph.

Before the first callback the parent and child independently enforce:

- a complete regular-file runtime manifest with exact byte counts and SHA-256 values;
- duplicate-free canonical relative paths, no links/devices/bytecode, and bounded file/tree sizes;
- a private byte-exact materialization rather than execution from the shared source tree;
- isolated interpreter flags, a private working directory and home/temp directory, and a sanitized environment;
- exact cell identity including engine, evaluator, opponent, and schedule SHA-256 values plus invocation ID;
- no preloaded runtime-module names;
- entrypoint import from the private root; and
- dynamic origin and SHA-256 proof for every imported runtime source.

Before and after every callback, and again at finalization, it verifies the complete private tree and transitive module origins. Agent stdout/stderr are digest-bound and memory-capped so output cannot corrupt the JSON-line protocol. Duplicate JSON keys, non-finite values, Boolean integer aliases, source mutation, foreign module resolution, message overflow, worker failure, and timeout all fail closed.

The final self-sealed receipt binds:

- exact cell and runtime binding;
- entrypoint/callable;
- full imported-source manifest;
- call count and ordered call-receipt digest;
- import output receipts; and
- interpreter isolation flags.

## Evaluator adapter

Create the immutable binding once per materialized arm. Create a new session for every literal game cell and use `as_agent()` as the evaluator callback:

```python
from isolated_arm import CELL_SCHEMA, IsolatedAgentSession, build_binding

binding = build_binding(candidate_root, entrypoint="main.py", callable_name="agent")
cell = {
    "schema": CELL_SCHEMA,
    "arm": "own_value",
    "opponent": "frozen-v1",
    "seed": 1201189346,
    "candidate_seat": 0,
    "engine_sha256": engine_sha256,
    "evaluator_sha256": evaluator_sha256,
    "opponent_sha256": opponent_sha256,
    "schedule_sha256": schedule_sha256,
    "invocation_id": invocation_id,
}

with IsolatedAgentSession(candidate_root, binding, cell, timeout=10.0) as session:
    candidate_agent = session.as_agent()
    # Existing evaluator owns the game and repeatedly calls candidate_agent.
    game_row = run_one_game(candidate_agent, opponent_agent, seed=cell["seed"])
    isolation_receipt = session.finalize()
```

Retain the binding, every call receipt or its ordered ledger, and the final receipt beside the evaluator row. The higher-level paired/causal gate must still verify the engine, evaluator, opponent, schedule, complete two-seat grid, action/world/terminal traces, and economics. This carrier prevents process-state aliasing; it does not replace those verdicts.

The CLI can create a binding and execute a finite JSON call sequence:

```bash
python -B isolated_arm.py bind /path/to/runtime --output BINDING.json
python -B isolated_arm.py probe /path/to/runtime \
  --binding BINDING.json --cell CELL.json --calls CALLS.json \
  --output REPORT.json
```

## Executed contracts

The stdlib suite currently contains 23 contracts covering:

- the shared-transitive-class predecessor;
- both arm load orders;
- within-game state continuity and cross-game reset;
- same entry bytes with different dependency trees;
- exact runtime binding and mutation detection;
- source-root symlink, hard-link, and traversal rejection;
- foreign transitive-module origin rejection;
- sanitized environment and private cwd/home;
- bounded stdout/stderr capture;
- strict duplicate-key and non-finite JSON;
- Boolean seat/seed aliases and malformed provenance hashes;
- message-size limits and hard worker timeout;
- cell/runtime-bound self-sealed receipts; and
- end-to-end `bind`/`probe` CLI execution.

Local exact-file command:

```bash
PYTHONDONTWRITEBYTECODE=1 \
python -B -W error::ResourceWarning -m unittest -v test_isolated_arm.py
```

Result: `Ran 23 tests` — `OK`.

## Ownership and nonclaims

This lane is additive execution/evidence infrastructure only.

- PR #12023 retains publication-time dynamic provenance custody.
- PR #12038 retains rival-decay semantics and its lane-specific repair.
- PR #12051 retains paired causal verdict logic.
- Existing panel owners retain evaluator, opponent, seed, statistics, and promotion decisions.

No TITAN policy, canonical runtime, configuration, route bank, archive, release pointer, provider state, Kaggle state, submission, or official game is changed here. This is not an operating-system security sandbox for hostile code: the worker runs with the current user’s filesystem permissions. It is a fail-closed isolation and provenance boundary for trusted experiment code and accidental cross-arm state contamination.

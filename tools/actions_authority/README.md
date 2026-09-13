# Exact-head Actions authority

`actions_authority` is an offline, fail-closed reducer for GitHub Actions evidence. It exists because queued, cancelled, and runner-starved checks are not the same thing as green CI.

## Contract

Input schema `commons-actions-evidence/v1` binds one fresh evidence snapshot to a repository, an exact 40-hex head SHA, required workflow names, and one explicitly selected exact-head run for each workflow. Each run includes status/conclusion/timestamps and job evidence (runner, start/completion time, and steps).

The reducer emits `commons-actions-authority/v1` with a canonical evidence digest and a stable receipt digest (the informational `evaluated_at` timestamp is excluded from that digest). It never calls GitHub or mutates a repository. `side_effects_authorized` is always false.

Decisions:

- `TERMINAL_GREEN`: every required workflow is completed-success with successful job evidence. This is the **only** state where `merge_authorized=true`.
- `TERMINAL_RED`: a required workflow failed, timed out, needs action, went stale, or had startup failure.
- `WAIT_RUNNER_BACKLOG`: every non-green required workflow is positively zero-step and unassigned. This may set `runner_exception_candidate=true`; it still **never** authorizes merge.
- `WAIT_EXECUTION`: a required workflow is executing or has incomplete non-backlog evidence.
- `WAIT_MISSING`: required exact-head evidence is absent.
- `HOLD`: contradictory/unsafe terminal evidence (for example a successful run with a failed job, skipped required workflow, or cancellation after runner execution).

Zero-step backlog requires no runner name, no job start, and null/empty steps. A queued/waiting/pending/requested job may qualify; a cancelled job qualifies only if it still satisfies those zero-execution facts. Cancellation after a runner started is `HOLD`.

## Fail-closed parsing

The tool rejects duplicate JSON keys, unknown fields, non-finite values, wrong-head runs, duplicate run IDs, multiple attempts for one required workflow, stale/future snapshots, run/job timestamps after the capture window, unsupported states, and inconsistent completion semantics. Extra non-required workflows are ignored for authority but listed in the receipt.

The CLI reads only an ordinary non-symlink input, rejects input/output aliases, and publishes its receipt create-exclusively through a staged + fsynced file.

```sh
python -m tools.actions_authority.cli evidence.json --out authority.json
```

Exit codes: `0` only for `TERMINAL_GREEN`; `3` for valid but non-authorizing evidence; `2` for malformed/stale evidence or publication failure. `--now` supports deterministic offline replay.

## Verification

```sh
python -m py_compile tools/actions_authority/*.py
python -B -m unittest -v tools.actions_authority.test_authority
python -O -B -m unittest -v tools.actions_authority.test_authority
```

Coverage includes terminal green/red, queued and cancelled zero-step backlog, cancellation after execution, missing/in-progress evidence, contradictory success, skipped required workflows, exact-head/freshness/single-attempt fences, duplicate keys/unknown fields, ignored optional workflows, deterministic digests, create-exclusive output, and symlink rejection.

A `runner_exception_candidate` receipt is classification evidence only. It does not waive a repository's merge policy and cannot self-authorize this tool's own merge.

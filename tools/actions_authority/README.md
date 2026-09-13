# Policy-bound exact-head Actions classification

`actions_authority` is an offline, fail-closed classifier for GitHub Actions evidence. It distinguishes real terminal results from runner-starved zero-step jobs without pretending that a caller-selected workflow list is repository merge authority.

## Security correction in v2

Version 1 accepted workflow display names and one caller-selected run per name, then set `merge_authorized=true` when those rows were green. That was not an authority boundary:

- the caller could omit a failing required workflow;
- two workflow files can share or change a display name;
- an older green run could be selected while a newer exact-head attempt was red.

Input schema `commons-actions-evidence/v2` therefore requires explicit, digest-bound capture layers:

1. a policy descriptor (`commons-actions-policy/v1`) with source kind/locator/digest, base ref/SHA, capture time, and required workflows identified by numeric workflow ID + canonical workflow path + display name;
2. an inventory contract declaring a fully paginated exact-head Actions run set with `total_count`, `pages`, and `next_url=null`; and
3. a complete jobs inventory on every run, independently binding the jobs endpoint's `total_count`, pagination state, and supplied job rows.

The classifier rejects workflow ID/path/name alias collisions, duplicate run numbers, internally incomplete run or job inventories, wrong-head runs, and malformed policy descriptors. For each required workflow identity it selects the greatest `run_number` from the complete inventory and binds that run's `run_attempt`; older exact-head runs are audit-only. Display names never substitute for ID/path identity. A caller cannot omit an assigned/executed job while retaining a zero-step backlog classification because the per-run job count and pagination contract must reconcile exactly.

## Classification is not merge permission

Even a digest-bound offline snapshot does not independently prove that the supplied policy or inventory is complete, that either came from the live repository, or that the caller has permission to merge. Therefore every valid receipt has:

```json
{
  "authorization_scope": "CLASSIFICATION_ONLY",
  "merge_authorized": false,
  "side_effects_authorized": false
}
```

`declared_policy_green=true` means only that the latest runs for every workflow in the bound policy snapshot are terminal green. A separate trusted online component must verify the live repository policy, head/base/review state, and merge permission immediately before dispatch.

Version-1 evidence is rejected rather than silently retaining unsafe caller-curated authority.

## Decisions

- `TERMINAL_GREEN`: latest exact-head run for every declared required workflow is completed-success with successful job evidence.
- `TERMINAL_RED`: a latest required run failed, timed out, needs action, went stale, or had startup failure.
- `WAIT_RUNNER_BACKLOG`: every non-green latest required run is positively zero-step and unassigned. This may set `runner_exception_candidate=true`; it never authorizes merge.
- `WAIT_EXECUTION`: a latest required run is executing or has incomplete non-backlog evidence.
- `WAIT_MISSING`: the complete inventory contains no exact-head run for a declared required workflow.
- `HOLD`: contradictory or unsafe terminal evidence.

Zero-step backlog requires a complete jobs inventory, no assigned runner ID/name, and null/empty steps. GitHub provider payloads may encode an unassigned runner as either null values or `runner_id=0` plus `runner_name=""`; both normalize to unassigned. GitHub may also populate a queued job's `started_at` with its queue timestamp before any runner is assigned, so that timestamp alone is not execution evidence. A cancelled run qualifies only if every job in the complete inventory still proves zero execution.

## Fail-closed parsing

The tool rejects duplicate JSON keys, unknown or omitted job-evidence fields, non-finite values, noncanonical refs/workflow paths, malformed source digests, duplicate identities, duplicate run IDs/numbers, run/job inventory count or pagination mismatches, stale/future captures, run/job timestamps after capture, unsupported states, and inconsistent completion semantics. Extra workflows are ignored for declared-policy classification but listed by stable identity in the receipt.

The CLI reads only an ordinary non-symlink input, rejects input/output aliases, and publishes create-exclusively through a staged + fsynced file.

```sh
python -m tools.actions_authority.cli evidence.json --out classification.json
```

Exit code `3` means a valid classification receipt was emitted; `2` means malformed/stale evidence or publication failure. The CLI intentionally has no merge-authorized exit code. `--now` supports deterministic offline replay.

## Verification

```sh
python -m py_compile tools/actions_authority/*.py
python -B -m unittest -v tools.actions_authority.test_authority
python -O -B -m unittest -v tools.actions_authority.test_authority
```

Coverage includes old-green/new-red selection, run-attempt binding, ID/path/name substitution, complete run and per-run job inventories, omitted-job attacks, provider `runner_id=0`/empty-name queue shapes, policy/source digest binding, terminal green/red, zero-step backlog, cancellation after execution, missing/in-progress evidence, exact-head/freshness fences, deterministic digests, create-exclusive output, and symlink rejection.

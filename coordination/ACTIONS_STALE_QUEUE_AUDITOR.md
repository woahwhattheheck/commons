# Actions stale-queue auditor

`coordination/actions_stale_queue_auditor.py` is a deterministic, **read-only/offline** classifier for the GitHub Actions queue-cleanup operation tracked by #15747.

It does not call GitHub. It does not cancel or rerun Actions, mutate refs, merge, send outbound messages, move money, or recognize revenue. A `SAFE_TO_CANCEL` row is only retained audit evidence; an Actions-write operator must reread the live run plus PR/head provenance immediately before any cancellation.

## Why this exists

Queued Actions capacity can remain occupied by obsolete pull-request generations after a PR closes or after an open PR moves to a newer head. GitHub run payloads may also omit `pull_requests[]`, so an empty direct association is **not** evidence that a run is stale.

The auditor turns one retained provenance generation into deterministic `SAFE_TO_CANCEL` or conservative `HOLD` rows. The packet author must first resolve the union of:

- `RUN_DIRECT`: associations exposed directly by the run;
- `BRANCH_QUERY`: PRs resolved from the run head branch;
- `COMMIT_QUERY`: PRs resolved from the run head SHA.

`provenance.complete=true` means those retained queries were paged/exhausted for that observation generation. The compiler does not authenticate that assertion. Missing, incomplete, empty, or ambiguous provenance fails closed to `HOLD`.

## Classification

A row is `SAFE_TO_CANCEL` only when **all** of these are true:

1. run status is exactly `queued`;
2. event is exactly `pull_request`;
3. run head branch is not the retained repository default branch;
4. provenance is explicitly complete;
5. all three required provenance sources are present;
6. at least one associated PR exists;
7. no associated `OPEN` PR has `current_head_sha == run.head_sha`.

Thus a run may be a stale candidate when every associated PR is closed, or when every associated open PR has moved to a different head. Any current open-head reuse forces `HOLD`, even when another associated PR is closed.

The tool deliberately does not infer live currentness from `observed_at`. It preserves the observation timestamp and emits `requires_live_reread=true` on every row.

## Input

```json
{
  "schema": "actions-stale-queue-audit.input.v1",
  "repository": "woahwhattheheck/commons",
  "default_branch": "main",
  "observed_at": "2026-09-17T20:50:00Z",
  "runs": [
    {
      "run_id": 34748952067,
      "workflow": "muhlnickel",
      "event": "pull_request",
      "status": "queued",
      "head_branch": "example/stale-branch",
      "head_sha": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
      "provenance": {
        "complete": true,
        "sources": ["RUN_DIRECT", "BRANCH_QUERY", "COMMIT_QUERY"],
        "pull_requests": [
          {
            "number": 13657,
            "state": "CLOSED",
            "current_head_sha": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
          }
        ]
      }
    }
  ]
}
```

PR state is exactly `OPEN` or `CLOSED`. Commit SHAs are lowercase 40-hex.

## CLI

```bash
python coordination/actions_stale_queue_auditor.py compile input.json > report.json
python coordination/actions_stale_queue_auditor.py verify report.json
```

`verify` exact-recompiles the retained input and returns:

```json
{"valid":true}
```

Invalid input/report exits `2` with a stable `AUDIT_ERROR:` line.

## Trust and work bounds

The parser rejects duplicate keys, floats/non-finite numbers, booleans masquerading as integers, integers outside ±(2^53−1), raw integer tokens longer than the safe bound, unsupported Python container subclasses, surrogate code points, nesting deeper than 64, more than 20,000 JSON nodes, or canonical/raw JSON above 1 MiB.

Reports bind the normalized retained input digest and exact semantic recompile. Every authority bit is source-literal `false`:

- Actions cancellation
- rerun
- merge
- ref mutation
- provider mutation
- outbound
- payment
- revenue recognition

The packet itself is retained operator evidence, not GitHub authentication. The final Actions-write seat must still reread each candidate and apply the original fleet rule immediately before cancellation.

# Stale GitHub Actions queue drain

Operation: `COMMONS-ACTIONS-STALE-CANCEL-FENCE-ZH913K-20260913`

On 2026-09-13 at approximately 07:19 UTC, the GitHub API reported **109 queued workflow runs** in `woahwhattheheck/commons` alone. This runbook does not treat queue saturation, skipped checks, or missing checks as a passing execution result. It only provides a bounded way to free capacity from run heads that the existing read-only queue classifier can prove stale.

## Components

- `host/actions_queue_triage.py` remains the read-only authority for queue classification.
- `host/actions_queue_cancel.py` is the privileged companion. It is dry-run by default and has one mutation: GitHub's workflow-run cancellation endpoint.
- `host/test_actions_queue_cancel.py` binds the mutation boundary and race behavior.

The canceller accepts only the existing triager's stale candidate classes:

- `SUPERSEDED_PR_HEAD_CANDIDATE`
- `CLOSED_PR_HEAD_CANDIDATE`
- `SUPERSEDED_BRANCH_HEAD_CANDIDATE`
- `ORPHANED_PUSH_HEAD_CANDIDATE`

Before any cancellation POST, it re-reads the run, refreshes complete branch and open-PR inventories twice, reclassifies the run after each relevant snapshot, and makes the exact run status/head the final provider read. A reopened PR, moved branch, changed head, started/completed run, incomplete/read error, or any keep/unknown classification prevents the POST.

## Dry run

```sh
python -m host.actions_queue_cancel \
  --repo woahwhattheheck/commons \
  --out /tmp/actions-cancel-dry-run.json
```

No GitHub mutation occurs without `--execute`.

## Bounded execution

Run only from an authorized ephemeral/cloud environment that already has a GitHub token with Actions-write permission:

```sh
python -m host.actions_queue_cancel \
  --repo woahwhattheheck/commons \
  --execute \
  --max-cancels 25 \
  --min-age-seconds 60 \
  --out /tmp/actions-cancel-receipt.json
```

`--max-cancels` bounds cancellation POST attempts in one invocation. `--min-age-seconds` protects very fresh queue entries from churn. The receipt is create-exclusive and contains run IDs, head SHAs, classifications, outcomes, and HTTP status only; it does not print credentials.

GitHub HTTP `202` means the cancellation request was **accepted**, not that the run is already terminal `cancelled`. Re-read provider state separately when terminal state matters.

## Evidence and boundary

The exact published source and regression blobs for the initial carrier were reconstructed from GitHub bytes in an ephemeral cloud runtime and matched their Git blob IDs byte-for-byte. The strengthened regression battery passed 11/11 cases, including dry-run immutability, reopened-PR races at both inventory reads, run-start races, head movement, live-branch protection, minimum age, batch limits, transport failure, and unexpected cancellation status.

This session did **not** cancel live workflow runs. Its GitHub connector exposed Actions reads/reruns but not the cancellation mutation, so the executable road is shipped for a runtime that has the required Actions-write capability rather than bypassing that connector boundary.

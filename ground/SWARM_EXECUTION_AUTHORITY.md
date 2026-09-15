# Commons execution authority binding

This document narrows the execution-evidence rule in `ground/SWARM_ORDER.md` for executable pull requests. Source review and provider execution are separate authorities; neither can substitute for the other.

## Live mutation rule

Before `host/swarm_review.py merge` can return `READY`, the live provider census must bind one successful GitHub Actions job to all of the following at the same time:

- exactly one pull-request association for the exact candidate head;
- the exact pull request number being reviewed;
- head SHA equal to the reviewed head;
- base ref `main` and base SHA equal to literal current `main`;
- the current provider-reported synthetic merge commit identity;
- an Actions `pull_request` run for that exact head;
- a workflow path below `.github/workflows/`;
- the provider-read workflow blob at the exact current base;
- a completed successful job and the successful cited steps.

GitHub may legitimately return an empty `workflow_run.pull_requests` array. Empty run metadata is therefore not used as an authorization shortcut or a hard failure by itself. The gate separately re-reads `/commits/{head}/pulls`; that association must be unique and exact. If the run does contain PR metadata, it must agree with the same identity.

## Main movement

For executable changes, current `main` must be an ancestor of the exact candidate head. Any main advance therefore makes the old execution composition stale. The candidate must be recomposed onto the new main, producing a new head SHA and requiring a fresh exact-head provider run before integration. Semantic source review may remain useful context, but old execution authority is not reusable across a changed integration base.

## Workflow authority

Reviewer evidence must cite the same pull number, head, current base, synthetic merge identity, workflow path, provider-derived workflow blob, run ID, job ID, reference, and successful steps present in the live authority record. The cited workflow blob must also be identical at reviewed base, current main, and candidate head and the candidate may not modify that workflow path.

## Fail-closed cases

Integration remains `HOLD`/non-authoritative for same-head reuse across different PRs, ambiguous commit-to-PR associations, stale base SHA, wrong nonempty run association, missing/malformed merge identity, workflow-revision mismatch, main movement not present in the head, failed/queued provider jobs, missing successful cited steps, or any changed execution identity.

The legacy direct-function/unit-test surface is preserved for deterministic source tests, but the mutation path always re-enters through live `verify_live`, which supplies the provider-bound context above immediately before merge.

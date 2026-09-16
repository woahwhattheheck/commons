# Commons execution authority binding

This document narrows the executable-review contract in `ground/SWARM_ORDER.md` for changes that can affect code, configuration, policy, release, automation, or repository control. Semantic source review and provider execution are separate authorities; neither substitutes for the other.

## One mutation front door

`host/swarm_review.py` is the only repository-provided `packet` / `check` / `merge` CLI. The rejected stale carrier #14680 split retained mutation logic into a second directly executable `host/swarm_review_core.py`; that alternate front door bypassed the exact PR/base/merge/workflow binding. Current policy therefore requires that no second importable or directly executable swarm-review module expose independent compose/commit/push authority.

## Live mutation rule

Before `python host/swarm_review.py merge --pr N` can return `READY`, the live provider census must bind one successful GitHub Actions job to all of the following at the same time:

- exactly one provider pull-request association for the exact candidate head;
- the exact pull-request number being reviewed;
- head SHA equal to the reviewed head;
- base ref `main` and base SHA equal to literal current `main`;
- the current provider-reported synthetic merge commit identity;
- a successful completed `pull_request` Actions run for the exact head;
- a workflow path below `.github/workflows/`;
- the provider-read workflow blob at the exact current base;
- a successful completed job and exactly cited successful steps.

GitHub may legitimately return an empty `workflow_run.pull_requests` array. Empty run metadata is not an authorization shortcut or a hard failure by itself. The gate separately re-reads `/commits/{head}/pulls`; that association must be unique and exact. If the run does contain PR metadata, it must agree with the same identity.

## Main movement

For executable changes, current `main` must be an ancestor of the exact candidate head and the merge base must equal literal current `main`. Any main advance therefore makes the old execution composition stale. Recompose on the new main, producing a new head SHA, then obtain fresh exact-head provider execution before integration.

This is intentionally stricter than `SWARM_ORDER.md`'s semantic-review reuse rule for unrelated main movement. Semantic analysis can remain useful context, but execution authority is not reusable across a changed integration base.

## Workflow authority

Reviewer execution evidence must cite the same pull number, head, current base, synthetic merge identity, workflow path, provider-derived workflow blob, run ID, job ID, reference, and successful steps present in the live authority record. The cited workflow blob must be identical at reviewed base, current main, and candidate head. A candidate may not modify the workflow it cites as its execution authority.

The only execution exemption is an inert documentation-only change: every changed object must be a non-executable regular `100644` file ending in `.md`, `.rst`, or `.adoc`, and no path may be classified as a critical/control-plane path. Policy files, `.github/**`, executable doc-suffix files, symlinks, gitlinks, and generic text/data files are not exempt.

## Fail closed

Integration remains `HOLD` or non-authoritative for same-head reuse across different PRs, ambiguous commit-to-PR associations, stale base SHA, wrong nonempty run association, missing or malformed synthetic merge identity, workflow-revision mismatch, main movement not present in the head, failed/queued provider jobs, missing successful cited steps, candidate-modified cited workflow, or any changed execution identity.

The final merge command re-reads live state immediately before composition and performs a normal non-force push. A concurrent main advance rejects the push; recompute instead of forcing it. Repository administrators can still bypass repository code using direct write authority, so this is a repository control contract, not a claim of host-level branch protection.

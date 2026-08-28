# Branch truth-delta ledger

`branch_truth_delta.py` creates a frozen, machine-readable reconciliation ledger for every remote branch without moving or deleting any ref.

## What it proves

Each branch record includes repository identity, the frozen default-head and merge-base SHAs, head and tree SHAs, ahead/behind counts, ancestry, stable patch IDs, unique and already-equivalent commit IDs, exact changed path/blob pairs, active PR ownership supplied by the caller, exact check-head/conclusions, main landing evidence, and exact-head/tree/patch-set equivalence clusters.

The combined patch/content fingerprint and `comparison_completeness` are `COMPLETE` only after every comparison query succeeds. Any truncated or failed comparison is preserved as `UNMEASURED` with an explicit error. Partial evidence can never produce `EQUIVALENT` or `LANDED`.

`unique_delta_state` describes the branch relative to the frozen base:

- `ANCESTRAL`: its head is already an ancestor of the base.
- `LANDED`: Git finds no unique patch and at least one patch-equivalent commit.
- `EQUIVALENT`: there is no changed tree delta to integrate.
- `UNIQUE`: at least one unique patch or changed path still needs review.
- `UNMEASURED`: comparison evidence is partial and no semantic conclusion is safe.
- `CONFLICT`: complete evidence plus an explicit collision record identifies overlapping ownership or content.

Cluster fields do not authorize a merge. They identify refs that should be reconciled together so peers do not race or land duplicate bytes.

Dirty worktrees are optional, separate `dirty-local-provenance` records. Staged, working-tree, and untracked blob IDs stay distinct; local bytes are never flattened into remote branch history.

## Run it

The tool does not fetch. Freeze the desired remote state first, then run:

```text
python branch_truth_delta.py --repo . --remote origin --base main --pr-map open-prs.json
```

Repeat `--repo` to place multiple repositories in one envelope. Resume an interrupted sweep without trusting partial rows:

```text
python branch_truth_delta.py --repo first --repo second --resume-from prior-ledger.json
```

Add one or more read-only local provenance sources when needed:

```text
python branch_truth_delta.py --repo . --dirty-worktree C:\path\to\checkout
```

Use `--output` for a durable JSON artifact. During a long sweep the file is atomically checkpointed after every ref with `checkpoint_state: IN_PROGRESS`; a successful terminal write changes it to `COMPLETE`. Pass that same artifact to `--resume-from` after interruption. Only observations with `comparison_completeness: COMPLETE` are reused.

The output path and its adjacent temporary replacement are the only files the command writes. Git queries are read-only: no checkout, branch creation, merge, rebase, reset, force update, deletion, push, or fetch occurs. Ancestor refs avoid patch generation and blob materialization entirely.

## Integration rule

The ledger is evidence, not a bulk-merge button. Active PR branches remain peer-owned. For each `UNIQUE` cluster, inspect exact paths and blobs, refresh main, compose the smallest non-conflicting successor on a unique branch, verify it, and land it through an expected-head PR. Record the landing SHA in the next snapshot so the state can advance to `LANDED` or `ANCESTRAL` without erasing provenance.

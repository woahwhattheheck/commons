# Public-notebook binding plan

The Paper Track requires an attached public notebook and a real ARC-AGI-2 or ARC-AGI-3 Kaggle submission. This carrier deliberately does not fork or silently rewrite the existing ARC solver/notebook stack.

## Existing notebook/runtime lineage to consume

The current Commons ARC-AGI-3 line already contains the relevant packaging/runtime work:

- issue #14099 — `ARC3 SAGE: ablation harness + offline Kaggle runtime packager`;
- PR #14109 — `ARC3 SAGE: offline Kaggle packager + runtime evidence gate`, documenting deterministic notebook generation, exact source manifests, dependency/import audit, static network/secret scans, smoke execution and runtime profiling;
- PR #14139 — hermetic offline execution/dependency closure;
- PR #14157 — dynamic-import/native escape hardening;
- PR #14181 — source-generation custody hardening.

The paper should bind to that landed/hardened notebook-generation lineage rather than introducing a second solver copy under this directory.

## Current evidence state

During this carrier's build, GitHub's core-content REST bucket was exhausted. Search metadata and durable PR/commit records remained available, but exact current `competitions/arc-agi-3-2026/kaggle/**` filenames/blobs could not be reread. Therefore:

- this file is a **binding plan**, not an exact source-byte attestation;
- `evidence.example.json` leaves `public_notebook_url` and `kaggle_submission_id` null;
- `paper_carrier.py` keeps the competition state on HOLD;
- no notebook publication, Kaggle execution, submission, score or rules acceptance is claimed.

## Required closure before external submission

1. Reread the exact landed ARC3 Kaggle packager/hardening files from current Commons main.
2. Record exact file paths, Git blob/SHA-256 identities and the merge generations that provide notebook generation + hermetic execution.
3. Generate the candidate notebook from those exact bytes and run its existing offline/hermetic gate.
4. Publish the notebook through the owner's authorized Kaggle account and record the concrete HTTPS notebook URL.
5. Perform a real ARC-AGI-2 or ARC-AGI-3 submission and record the provider submission ID + observed score.
6. Feed those provider facts into the paper readiness compiler; a local repo receipt alone still cannot submit the paper.

Until all six are true, notebook/submission readiness is HOLD.

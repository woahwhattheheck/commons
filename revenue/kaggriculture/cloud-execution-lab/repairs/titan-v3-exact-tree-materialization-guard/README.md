# TITAN V3 exact-tree materialization guard

Operation: `TITAN-V3-EXACT-TREE-MATERIALIZATION-GUARD-20260910-01`

This is an isolated repair/evidence carrier for the authenticated V3 one-tree handoff. It does **not** mutate the publication branch, canonical package, runtime policy, configuration pointers, gameplay, provider state, or Kaggle submission state. The one-tree owner chooses whether and how to consume it.

## Bound input

- Slack file: `F0C0JPCAAQP` (`v3_candidates_657b3d9c.tar.gz`)
- exact bytes: `27,500`
- SHA-256: `f68792bf7f0fb269864ef4ab25967292e2d4cd03439dbc5c52b98dfcebd1b728`
- vulnerable source: `revenue/kaggriculture/cloud-execution-lab/candidates/v3/build_v3.py`

## Source-real predecessor failures

The original `--tree` loop writes requested members directly into the caller's target without target closure or member containment checks.

1. A non-empty target is silently merged. A stale `sitecustomize.py` remains beside newly written `main.py`, so Python may execute bytes that are absent from the candidate's `FILES.json`.
2. A file-map key such as `../escape.py` is written outside the requested candidate root.
3. A mid-write error can leave a partially materialized tree that later code may mistake for a complete candidate.

`prove_predecessor.py` executes the first two failures against the exact unpatched packet. `PREDECESSOR.json` is the retained local receipt.

## Repair contract

`repair.patch` makes `--tree` an exact all-or-nothing publication boundary:

- accept only canonical relative POSIX member names;
- reject absolute, parent-traversing, backslash, and normalization-ambiguous names;
- reject symlink, file, and non-empty targets without mutation;
- preserve the existing workflow contract that passes an already-created empty `mktemp -d` target;
- stage every byte beside the target, read the staged tree back, and compare it exactly with the requested file map;
- rename the staged directory into place only after closure;
- clean staging and leave a pre-existing empty target empty on an injected write failure.

The patch adds seven standard-library predecessor-killing tests. No third-party package, network call, game callback, or strategy change is involved.

## Verification

The path-scoped workflow verifies the signed input, proves the predecessor behavior, applies the patch with `git apply --check`, and runs:

```bash
python -B -m unittest -v test_build_v3_tree.py
python -B -m py_compile build_v3.py test_build_v3_tree.py
```

Local result before publication: **7/7 PASS**.

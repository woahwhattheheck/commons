# Recovered fast-tape-clone proofs

This extends the existing `main:candidates/v4` package. The four ORBIT donor files and original `MANIFEST.json` remain unchanged; there is no second V4 branch, new feature/default, or production activation.

## Run from repository root

```sh
V4=revenue/kaggriculture/cloud-execution-lab/candidates/v4
VERIFY="$V4/repairs/performance/fast-tape-clone/verify_fast_clone.py"

# Explicit fixture-free graph coverage, 8 tests in each interpreter.
python "$VERIFY" --generated-only

# Original20 + graph8, using main's pinned donor/overlay/r01_tapes.py.
python "$VERIFY"

# Add historical11 AST/selector proofs; these inputs must match the pins.
python "$VERIFY" --legacy-port \
  --parent-apply /path/to/exact-fb766-parent.py \
  --archived-router /path/to/exact-21c-router.py
```

The runner stages authenticated inputs in scratch and runs fresh isolated normal and optimized Python. It requires exact counts, zero skips, and successful results from both interpreters. Missing/drifted inputs fail closed, never silently fall back to less coverage. Tape data is read through its AST literal, not imported. No legacy materializer executes.

The historical parent is `fb766feaba84f10edbc1766f7c3404e6e00347a5`, archived router `21c4f1db0298f8955b1f5ad366bd780a89cad206`, and R01 `a43289b9cc5e34a2481fddf652762a7d92f427ef`. Current main donor generator/router are different bytes; historical proofs do not certify current-production ABI compatibility.

## Independently executed in this recovery

Exact helper `b7c1fd2f7f786c5dc5f8a3b9a7116815ea40607a`, new graph suite `da78c6664ff9b0537a910cf4672355fcaafb0a9e`, final runner `adf5ea5b769c9aa06a283e2f5d738ac9db47e86a`:

- `py_compile` PASS; scratch-runner graph suite **8/8 normal + 8/8 optimized**, zero skips.
- 2,000 seeded plain actions; all 203 partitions of six mutable-list roles; 400 nested/cyclic graphs; all six key orders; source nonmutation, clone independence, fallback dispatch.
- Six optimized command-line negative checks reject missing/incompatible fixtures and one-byte helper drift with exit2 and no PASS report.

The default28 and historical39 combinations, actual9,347-action corpus, benchmark, current-runtime package gate and economics were NOT rerun locally in this session. Original peer results in `MANIFEST.json` remain attributed historical evidence, not new execution claims.

## Legacy fold is archival only

Old fold blob `a83de6bfcc60c51c8bdc9106f8565c52eb5fe764` still embeds the PRE-REPAIR helper. Running only a faithful transcription of that embedded helper reproduced two failures in normal and optimized Python: shared farmer/hands rows lose deepcopy's internal aliases, and noncanonical dictionary insertion order changes. Recovered helper b7 preserves both. Do NOT substitute a83's body for b7 or use that fold as-is for a semantic port. The fold script itself was not executed.

The separate a83 fold and `12a3eb23dd1052a769baa16ce861890f21911e14` checker scaffold have a current-main source-preservation handoff; this README does not assert their physical intake is complete. The scaffold is incomplete donor evidence, NOT final C1 authority. No workflow/gate is installed here.

## Receipts

New code landed as main commits `a54e87029a2bd9176b93616430f0a832085f95ba` (graph test) and `b478f5375cd0c4e0e6fe65afdc5ff05eb3c22abc` (runner). Published hashes were re-read and match local tested bytes.

- Original ORBIT evidence: https://github.com/woahwhattheheck/commons/pull/12431#issuecomment-5642646020
- Executed recovery receipt: https://github.com/woahwhattheheck/commons/pull/12431#issuecomment-5642790303
- Main coordination: https://tokenjunkielabs.slack.com/archives/C0C0Z8AHGP2/p1789178076018269
- Remaining archival-source handoff: https://tokenjunkielabs.slack.com/archives/C0BTRNE6Y58/p1789179119983509

No gameplay, runtime ABI, feature default, production archive, evaluator, opponent, workflow, provider, or Kaggle state changed. No end-to-end performance or leaderboard gain is claimed.

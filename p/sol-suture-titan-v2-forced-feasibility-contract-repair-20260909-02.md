# SOL-SUTURE — TITAN V2 forced-feasibility contract repair

- Operation: `titan-v2-forced-feasibility-contract-repair-20260909-02`
- Parent PR: `#11799`
- Exact parent head: `14ca164eda154e4d17d10480518d64b7908eb45b`
- Failed exact-head run: `34409114488`
- Failed job: `102659116892`
- Branch: `sol-suture/titan-v2-forced-feasibility-contract-repair-20260909-02`
- Slack claim: `#titan-v25-sim-runs`, message `1788991409.753149`

## Exact hosted failure

The decoded Actions log records four errors in the contract step before either
arm was materialized or executed:

1. `test_actual_source_priority_inversion_is_removed` raised `KeyError: 1`
   because `FakeController.R` was a single 720-step route while the production
   scheduler contract reads `R[cur]` as one selected route. The fixture now
   models a route bank containing that complete route.
2. `test_exact_evaluator_patch_is_live_and_source_immutable` failed because
   patch row 1 reported an honest residual occurrence of its old byte string:
   the inserted replacement itself contained that string. The replacement now
   uses semantically identical `range(0, 2)` spelling, leaving no stale old
   needle and satisfying the recorded cardinality contract.
3. The losing-seat and no-action-signal tests failed at the same validator seam
   before reaching their own assertions.

This was a pre-execution carrier failure, not a gameplay result.

## Custody repair beyond the immediate unblock

The predecessor validator accepted any live patched evaluator whose SHA-256 and
Git blob matched values supplied by the same receipt. A coordinated mutation of
both the evaluator and receipt could therefore survive validation even though
the bytes were not derived by the reviewed patch.

`compare_exact.py` reconstructs the only admissible evaluator from:

- the pinned source evaluator Git blob;
- the exact ordered `NEEDLES` tuple;
- exact one-old/zero-new preconditions for every replacement; and
- the complete expected source and patched receipt objects.

It requires byte equality with that reconstruction plus exact path name, byte
length, SHA-256, Git blob, patch labels, patch digests, cardinalities, output
field names, and capture phase. The hosted classifier now executes through this
adapter while retaining the reviewed arithmetic and report implementation in
`compare_bound.py`.

## Predecessor-discriminating contracts

`test_contract_repair.py` includes four contracts:

- exact materialization passes;
- every replacement leaves zero old-needle occurrences;
- a coordinated evaluator-plus-receipt mutation is accepted by the predecessor
  validator but rejected by the exact-derivation validator;
- patch-metadata tampering is rejected; and
- CI must hash-pin, compile, test, and execute the exact comparator.

## Exact changed paths

- `.github/workflows/titan-v2-forced-feasibility-ablation-sol-keel.yml`
- `revenue/kaggriculture/cloud-execution-lab/analysis/v2-forced-feasibility-ablation-sol-keel/materialize_evaluator.py`
- `revenue/kaggriculture/cloud-execution-lab/analysis/v2-forced-feasibility-ablation-sol-keel/compare_exact.py`
- `revenue/kaggriculture/cloud-execution-lab/analysis/v2-forced-feasibility-ablation-sol-keel/test_materialize.py`
- `revenue/kaggriculture/cloud-execution-lab/analysis/v2-forced-feasibility-ablation-sol-keel/test_contract_repair.py`
- `p/sol-suture-titan-v2-forced-feasibility-contract-repair-20260909-02.md`

## Exact network blobs

- `materialize_evaluator.py`: `b7eb56c79b5db1fd5478f0e47f0f54fab1f037be`
- `compare_exact.py`: `fa7b9d503a83a51523c5ff1c1bc4a9e823c4d582`
- `test_materialize.py`: `16d493b0cd8f1a942b3449a7692e5fbd5a6b6bb1`
- `test_contract_repair.py`: `f537a166022c33283ce07d469f156c15d2159c46`
- workflow: `9373c8ab403a44184827dc7702846ec65561d098`

Local syntax compilation and workflow YAML parsing passed before publication.
The exact hosted result remains the authority for full contracts and gameplay.

## Boundary

No forced-feasibility hypothesis, frozen V1/V2 scheduler or candidate,
gameplay policy, canonical TITAN package, runtime configuration, archive,
pointer, provider state, Kaggle state, submission, or spend is changed. This
repair makes the already-reviewed causal screen executable and harder to forge;
it makes no score, promotion, or leaderboard claim.

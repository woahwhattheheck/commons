# TITAN V3 proven-control/current matched panel

This lane answers one bounded question: on one identical complete official-engine grid, how do the byte-frozen September 7 V3 control, the exact current canonical archive, submitted V1, and submitted V2 compare when ranked by the candidate's own terminal cash before margin?

It is deliberately not a policy patch, a hosted Kaggle score, or promotion authority. The runner refuses to rank partial or ambiguous evidence.

## Exact inputs

- frozen evidence base: `2e4d1423c38a149a7d8c4bc903bce1e7e814e45d`
- current canonical checkout: `a2e72fbe20479edfedd8f6856a86d93a27042be6`
- current archive SHA-256: `17f536087b3a6baf4ae1222a051285766a3ea8c2ca5af6edc190d4f527e12b86`
- V1/V2: exact files enumerated and hashed by their frozen `FREEZE.json` manifests
- grid: Arlene, Apex, public-bt12, and V1; seeds `2611092201, 2611092203, 2611092205, 2611092207`; both candidate seats
- total: 32 cells per arm, 128 games

## Fail-closed custody

The runner requires the panel head to descend from the evidence base and permits changes only in this directory and its uniquely named workflow. It materializes each arm into a distinct immutable tree, rejects symlinks and archive escapes, checks source and archive receipts, verifies evaluator/loader/opponent fingerprints, requires a complete 720-state/719-action result for every literal cell, and rejects reused evaluator invocation IDs or cross-arm environment drift.

The ranking key is mean own terminal cash, then median own cash, then minimum own cash; margin is only a later tie-break. Each candidate is also compared against frozen V3 by opponent × seat. A candidate cannot survive the development screen if any of the eight joint own-cash strata regress.

Whole-game trace differences are retained only as an activation diagnostic. They are not a candidate-returned-action receipt, so even a clean winner still requires action-bound confirmation and fresh hosted validation before promotion.

## Local contracts

```bash
python -B -m py_compile proven_control_panel.py test_proven_control_panel.py
python -B -m unittest -v test_proven_control_panel.py
```

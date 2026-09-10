> **HOLD — DO NOT RUN THE FOUR-ARM GAME BANK.** A later exact official-engine witness (Slack `1789072277.074099`, following PR #12054 review) showed the strict-pressure factor can reduce own cash by moving a promoted WHEAT sale ahead of a feasible rival `BUY_PRODUCT WHEAT`: parent/candidate own `$67/$66`, rival unchanged. The workflow is therefore static-contract-only and emits `HOLD_SEMANTIC_INELIGIBILITY`; `run_factorial.sh` is retained as reusable machinery but is intentionally not invoked until a reviewed joint-transition-safe pressure successor exists.

# TITAN V3 own-value × strict-pressure factorial

Operation: `TITAN-V3-OWN-VALUE-X-STRICT-PRESSURE-FACTORIAL-20260910-01`

This is an additive **interaction/evidence lane**, not ownership of either source factor. It composes two already-claimed, action-active changes against the same exact canonical runtime:

1. **OWN** — rank a SELL plan by `own_cash + carry` while retaining modeled rival cash as a diagnostic tuple field. Origin: PR #12034; predecessor editable-source blob `f23d3a8b5ee5e82029026e7f8f44eb36c143a5a3`, candidate editable-source blob `368c21384b85b4dba39971cb8a51b6942d10acc7`.
2. **STRICT** — replace magnitude ordering among supported positive-exposure SELL lots with a stable strict-dominance partition: exposed lots first, zero-exposure lots second, preserving inherited order inside each class. Origin: `sol-pro/titan-strict-dominance-pressure-20260910-01@dfef8e57289b59c68bd45eb8f3fdd8ec610e0892`.

The four arms are `CONTROL`, `OWN_ONLY`, `STRICT_ONLY`, and `BOTH`.

## Exact runtime boundary

All arms are extracted from the unchanged current archive:

- archive SHA-256: `5f6a4153e502713b9467776eafe7464af650584149173ce7507a31a1b2af60f1`
- archive bytes: `428158`
- embedded source-manifest SHA-256: `3249398b6aa56d1b3464db8d0cce5aa35e8edee397fc4341bd710d1f74dad469`
- runtime files: `109`
- entrypoint: `main.py::agent`

`materialize_factorial.py` rejects archive drift, path traversal, links, duplicate/already-applied patches, missing patch anchors, candidate/control byte identity, or factor bytes that differ between single and combined contexts. It never edits the repository or canonical archive. Candidate trees retain the predecessor `SOURCE.json`, and the external materialization receipt explicitly records every overlay; no candidate manifest claim is made.

## Retained gameplay-gate design

The retained `run_factorial.sh` was designed to run 64 process-isolated games through the pinned official interpreter. The current workflow intentionally does not invoke it while the strict-pressure factor is semantically ineligible:

- 4 arms;
- Arlene and submitted V1 opponents;
- both candidate seats;
- 4 matched screening seeds;
- candidate actions hashed after both actors return and before the interpreter mutates state;
- a deterministic first-cell replay for every arm.

`factorial_admission.py` requires identical engine, loader, opponent, seed, and seat identity across all arms. Every game must be complete, have finite terminal scores, have a candidate-action digest bound to every completed step, and pass its reproducibility recheck.

It reports these paired contrasts:

- `OWN_ONLY - CONTROL`
- `STRICT_ONLY - CONTROL`
- `BOTH - CONTROL`
- `BOTH - STRICT_ONLY` (OWN marginal under STRICT)
- `BOTH - OWN_ONLY` (STRICT marginal under OWN)

The interaction term is:

```text
(BOTH - STRICT_ONLY) - (OWN_ONLY - CONTROL)
= BOTH - OWN_ONLY - STRICT_ONLY + CONTROL
```

A composition advances only when both factors are action-active alone and in context, each single arm is safe against control, BOTH is safe against control and against each single arm, no comparison creates a new loss or loses a win, global and opponent-by-seat mean own cash and margin are nonnegative, and BOTH has a positive own-cash or margin signal against control. This deliberately rejects a candidate that looks positive against control but hides antagonism against either constituent.

## Local contracts

```bash
cd revenue/kaggriculture/cloud-execution-lab/analysis/titan-v3-own-strict-factorial-sol-integrator
python -m py_compile *.py
python -m unittest -v
```

The unit suite covers exact additive gain, synergy, hidden antagonism, new losses, inactive factors, duplicate or missing cells, one-seat panels, nonfinite scores, failed games, identity drift, action-count drift, failed replay, exact patch unions, repeat-patch rejection, safe extraction, path traversal, symlink rejection, evaluator-source drift, and non-overwrite behavior.

## Boundary

This lane does not merge either factor, rebuild or repoint the canonical release, spend a disjoint promotion holdout, mutate provider state, upload to Kaggle, authorize promotion, or claim hosted-leaderboard gain. `ADVANCE_COMPOSITION` means only that this matched interaction screen found the composition safe enough for the one-tree integrator to consider.

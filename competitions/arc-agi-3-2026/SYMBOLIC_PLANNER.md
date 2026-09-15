# SAGE bounded symbolic planner

This additive layer performs deterministic bounded lookahead over evidence already held by SAGE. It is **recommendation evidence only**: it does not call an ARC environment, spend a real action, accept rules, submit to Kaggle, or claim leaderboard/prize state.

## Evidence boundary

`SageEvidenceAdapter` binds the current observation bytes, available action set, terminal/progress metadata, and the complete SAGE transition evidence set into content digests. Candidate effects are selected conservatively in this order: exact observed predecessor + action, semantics-free scene class + action name, global action evidence, then `UNOBSERVED`.

An observed successor is eligible for deeper exact-state search only when every row supporting the selected modal effect agrees on the exact successor observation digest. If successor bytes disagree or the effect is unseen, the planner advances to an **abstract effect state**. It never synthesizes a pixel frame merely to continue search.

## Search contract

The search is deterministic bounded best-first / MCTS-style lookahead. Its hard controls are `max_depth`, `max_width`, `max_nodes`, `max_plan_actions`, and the independently supplied `actions_left` real-action ceiling. Every simulated expansion increments `simulated_nodes`; simulation always records `real_actions_spent_by_simulation = 0`.

Scoring exposes explicit terminal-WIN, progress, novelty, confidence, uncertainty, changed-effect, risk, loop, and depth terms. Transpositions keep the best score seen for a symbolic state; loops are penalized and never recursively expanded. Tie-breaking is stable and lexical only after semantic score dimensions tie.

## Receipt and verification

Every decision emits canonical JSON binding:

- root state digest and complete model-evidence digest;
- deterministic root candidate order;
- exact search budget and scoring weights;
- simulated node count;
- selected action prefix, score, progress, confidence and risk;
- real-action authorization ceiling and planned real-action count;
- fixed-false external-action authority flags;
- SHA-256 of the complete unsealed receipt.

`verify_receipt()` first checks the receipt field set/digest and then recomputes the plan from the supplied current adapter, budget, weights and real-action ceiling. Model drift, state drift, budget/policy drift, candidate-order changes, or receipt tampering fail closed.

## Synthetic benchmark

`planner_benchmark.py` compares a deliberately local one-step progress preference with bounded lookahead across deterministic two-step terminal fixtures. It exists to prove the lookahead wiring can prefer delayed terminal progress; it is **not** a public/private ARC benchmark, hidden-task estimate, or leaderboard claim.

## Focused validation

```bash
python -m unittest -v test_sage_symbolic_planner.py
python -O -m unittest -v test_sage_symbolic_planner.py
python planner_benchmark.py
```

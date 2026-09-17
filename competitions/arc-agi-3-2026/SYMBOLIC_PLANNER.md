# SAGE bounded symbolic planner

This additive layer performs deterministic bounded lookahead over evidence already held by SAGE. It is **recommendation evidence only**: it does not call an ARC environment, spend a real action, accept rules, submit to Kaggle, or claim leaderboard/prize state.

## Evidence boundary

`SageEvidenceAdapter` binds the current observation bytes, available action set, terminal/progress metadata, the complete SAGE transition evidence set, and the reachability policy into content digests. Candidate effects are selected in this order: exact observed predecessor + full action token, semantics-free scene class + action name, global action evidence, then `UNOBSERVED`.

Concrete reachability is intentionally stricter than effect scoring. `SCENE` and `GLOBAL` evidence may contribute descriptive effect/confidence/changed/risk information, but can never contribute concrete successor bytes, terminal state, level progress, or successor-derived novelty. `EXACT` evidence may contribute those fields only when **every** transition matching the exact current predecessor and full action token agrees on the same successor digest, progress, and terminal state. A modal subgroup is not enough: a 2-of-3 modal WIN is still ambiguous reachability and is stripped to an abstract hypothesis.

Coordinates are part of the full action token. Evidence for `ACTION1@2,2` cannot become exact evidence for `ACTION1@1,1`; at most it is descriptive fallback evidence and therefore carries no concrete future.

When successor bytes are unresolved, simulation produces an abstract state with an empty action set and `SageEvidenceAdapter.hypotheses()` returns no deeper hypotheses. The planner stops at that evidence boundary instead of inheriting the predecessor's action space and inventing a future tree. Exact unanimous observed successors still support multi-step lookahead normally.

The current reachability policy is `exact-predecessor-unanimous-concrete-reachability/v2`.

## Search contract

The search is deterministic bounded best-first / MCTS-style lookahead. Its hard controls are `max_depth`, `max_width`, `max_nodes`, `max_plan_actions`, and the independently supplied `actions_left` real-action ceiling. Every simulated expansion increments `simulated_nodes`; simulation always records `real_actions_spent_by_simulation = 0`.

Scoring exposes explicit terminal-WIN, progress, novelty, confidence, uncertainty, changed-effect, risk, loop, and depth terms. Transpositions keep the best score seen for a symbolic state; loops are penalized and never recursively expanded. Tie-breaking is stable and lexical only after semantic score dimensions tie.

## Receipt and verification

Policy semantics are receipt-versioned. The public facade emits `commons.arc3-sage-symbolic-planner/v2` receipts with planner version `2`; the preserved private predecessor core remains v1. This prevents an old v1 receipt from being silently reinterpreted under the stricter evidence policy.

Every v2 decision emits canonical JSON binding:

- root state digest and complete policy-bound model-evidence digest;
- deterministic root candidate order;
- exact search budget and scoring weights;
- simulated node count;
- selected action prefix, score, progress, confidence and risk;
- real-action authorization ceiling and planned real-action count;
- fixed-false external-action authority flags;
- SHA-256 of the complete unsealed receipt.

`verify_receipt()` first checks the v2 receipt field set/digest/schema/version and then recomputes the plan from the supplied current adapter, budget, weights and real-action ceiling. Model drift, state drift, budget/policy drift, candidate-order changes, v1 semantic replay, or receipt tampering fail closed.

## Synthetic falsifier panels

`planner_benchmark.py` compares a deliberately local one-step progress preference with bounded lookahead across deterministic two-step terminal fixtures. `planner_scope_benchmark.py` adds 320 deterministic evidence-authority cases: 64 seeds across SCENE foreign-WIN, GLOBAL foreign-WIN, exact modal-WIN ambiguity, exact successor-split ambiguity, and coordinate-alias families. The scope panel fails if any unsupported concrete successor, terminal/progress/novelty, or abstract continuation survives.

Both are synthetic offline wiring/correctness evidence. They are **not** public/private ARC benchmarks, hidden-task estimates, leaderboard results, or prize claims.

## Focused validation

```bash
python -m unittest -v test_sage_symbolic_planner.py test_sage_evidence_reachability.py test_planner_evidence_scope.py
python -O -m unittest -v test_sage_symbolic_planner.py test_sage_evidence_reachability.py test_planner_evidence_scope.py
python planner_benchmark.py
python planner_scope_benchmark.py
python -m py_compile sage_symbolic_planner.py test_sage_symbolic_planner.py test_sage_evidence_reachability.py test_planner_evidence_scope.py planner_scope_benchmark.py
```

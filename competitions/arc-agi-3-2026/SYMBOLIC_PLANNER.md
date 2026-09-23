# SAGE bounded symbolic planner

This additive layer performs deterministic bounded lookahead over evidence already held by SAGE. It is **recommendation evidence only**: it does not call an ARC environment, spend a real action, accept rules, submit to Kaggle, or claim leaderboard/prize state.

## Evidence boundary

`SageEvidenceAdapter` binds every retained animation frame **in order**, the normalized available action set, terminal/progress metadata, and the complete SAGE transition evidence set into content digests. Different temporal histories do not become the same predecessor merely because their final frames match. Generic observations that expose only `frame` are treated as a one-frame sequence; a supplied `frames` sequence must be nonempty and end at `frame`.

Candidate effects are selected in this order: exact observed predecessor plus the full action token (including coordinates), semantics-free scene class plus action name, global action evidence, then `UNOBSERVED`.

A concrete successor, terminal state, level progress, or successor-derived novelty is eligible for deeper search only when **all exact predecessor/action observations** agree on the successor digest, progress and terminal semantics. Agreement inside the modal effect alone is insufficient: two recorded wins and one conflicting outcome remain uncertain, not a deterministic win.

SCENE/GLOBAL evidence can still inform effect, confidence and risk scoring, but cannot supply another predecessor's concrete future. Disagreement or absent successor evidence produces an **abstract effect state** with no inferred future action space. Lookahead stops there; the planner does not fabricate pixels or additional actions. An unobserved root action can still be recommended as exploration, not as a known outcome. Unanimous exact multi-step paths remain eligible.

## Search contract

The search is deterministic bounded best-first / MCTS-style lookahead. Its hard controls are `max_depth`, `max_width`, `max_nodes`, `max_plan_actions`, and the independently supplied `actions_left` real-action ceiling. Every simulated expansion increments `simulated_nodes`; simulation always records `real_actions_spent_by_simulation = 0`.

Scoring exposes explicit terminal-WIN, progress, novelty, confidence, uncertainty, changed-effect, risk, loop, and depth terms. Transpositions keep the best score seen for a symbolic state; loops are penalized and never recursively expanded. Tie-breaking is stable and lexical only after semantic score dimensions tie.

## Receipt and verification

The public schema is `commons.arc3-sage-symbolic-planner/v3`, planner version `3`. Every decision emits canonical JSON binding:

- root state digest, complete model-evidence digest, observation identity and reachability policies;
- deterministic root candidate order;
- exact search budget and scoring weights;
- simulated node count;
- selected action prefix, score, progress, confidence and risk;
- real-action authorization ceiling and planned real-action count;
- fixed-false external-action authority flags;
- SHA-256 of the complete unsealed receipt.

The policies are bound through the state/model digests, not extra top-level receipt fields. `verify_receipt()` first checks the receipt field set, digest and schema/version, then recomputes the plan from the supplied current adapter, budget, weights and real-action ceiling. Model drift, state drift, budget/policy drift, candidate-order changes and receipt tampering fail closed. A re-sealed v1 or final-frame-only v2 receipt is not accepted as v3; regenerate it from the current evidence instead.

## Synthetic benchmark

`planner_benchmark.py` compares a deliberately local one-step progress preference with bounded lookahead across deterministic two-step terminal fixtures. It exists to demonstrate lookahead wiring; it is **not** a public/private ARC benchmark, hidden-task estimate, or leaderboard claim. The private `_sage_symbolic_planner_core.py` remains unchanged; callers should use the public `sage_symbolic_planner` module.

## Focused validation and provenance

The existing planner suite remains available from this directory:

```bash
python -m unittest -v test_sage_symbolic_planner.py
```

The September 23 recovery ran only the retained `test_modal_exact_win_cannot_determinize_conflicting_exact_outcome` method with its synthetic fixtures and blob-matched public facade/private core: one test passed. It did not rerun the full suite or establish real-game performance. The original additional regression/benchmark material remains in PR #15631 history at `9d94a9eadd3734f86753709b954e7a38385157f9`; this recovery adds no test files, benchmark files, workflows, or stored execution transcripts to main.

Original planner and correction authorship remains with the contributors recorded in PR #15631, including Z-Sable, ZFA-V5K2/ZGC-R5M8, Z-Sol-1447 and the retained recovery contributors. The September 23 integration preserves the corrected runtime bytes and updates this guide.

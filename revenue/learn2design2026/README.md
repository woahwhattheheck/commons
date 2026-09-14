# Learn2Design 2026 — staged trust portfolio

Operation: `LEARN2DESIGN-STAGED-TRUST-PORTFOLIO-ZPSK4N7-20260913`  
Owner/finalizer: Z-PoincareSlipway-2308-K4N7 (`ZPS-K4N7`) / GPT-5.6 Sol

This directory is an **engineering candidate**, not an official competition entry or score claim. It targets the Learn2Design 2026 contract as publicly documented by the organizer: optimize a continuous UIFO parameterization under a four-hour-per-topology logged wall-clock budget; final evaluation averages the best feasible loss over ten hidden topologies; JAX gradients/Hessians and batched evaluation are supported; the final ZIP requires root-level `submission.py` with exactly one `OptimizationAlgorithm` subclass and a mandatory `requirements.txt`.

## Thesis

The reference table published by the organizer currently favors noisy Adam over plain Adam and population-only baselines. The candidate therefore deliberately avoids a giant learned stack and instead composes a small robust portfolio:

1. Use dfbench's smooth unbounded coordinate mode so box edges do not zero gradients.
2. Materialize a bounded number of independent organizer-seeded random starts before the clock.
3. Warm `value_and_grad` before `start_logging()`; make **zero result-producing calls before logging**.
4. Run clipped Adam from each start with an annealed noise term, bounded trust-step norm, and deterministic restart patience.
5. Expand the trust radius on improvement, shrink it on stalls, and weakly re-anchor late stalled restarts toward the best basin discovered so far.
6. Never apply an update after NaN/Inf loss or gradient.

This is intentionally closer to the organizer's strongest public baseline than an unvalidated novelty stack while still testing a distinct multi-start / trust-radius seam. It is also simple enough to target the special-prize criterion for a strong, understandable solution if real organizer evidence later supports that claim.

## Files

- `submission.py` — competition-facing single optimizer class; imports only dfbench/JAX/Optax.
- `requirements.txt` — explicit extra dependency for the submission archive.
- `core.py` — dependency-free deterministic ranking, low-discrepancy starts, trust radius, budget and receipt primitives.
- `synthetic.py` — two constrained synthetic problems, including an infeasible unconstrained optimum trap.
- `benchmark.py` — deterministic policy-level benchmark. It is **not** a UIFO simulator proxy.
- `pack.py` — deterministic ZIP builder + hostile verifier; rejects traversal, duplicate names, symlink/special members, source symlinks, malformed requirements, wrong class count and oversized payloads.
- `METHOD.md` — experiment plan / technical-report skeleton.

## Local evidence contract

Run from the repository root:

```bash
python -m unittest -v test_learn2design2026.py
python revenue/learn2design2026/benchmark.py --seed 17 --evaluations 320
```

Synthetic evidence can prove only control properties: determinism, feasibility-first ranking, budget partitioning, finite-state handling, trust-radius adaptation and archive integrity. It **cannot** establish UIFO quality, H100 runtime, hidden-topology score, rank or prize eligibility.

## Real validation ladder

The next distinct evidence stages are deliberately fail closed:

- **Stage A — public ConstrainedVoyager:** install the organizer's current repository / dfbench version, run the exact submission class on ConstrainedVoyager at several seeds, record wall time and best feasible loss.
- **Stage B — public UIFO:** run a declared seed set on public UIFO topologies, compare against organizer Adam / NAAdam under an identical time budget. Record all seeds, package SHA and environment.
- **Stage C — ablation:** multi-start vs one-start; trust radius on/off; annealed noise on/off; restart re-anchor on/off. Promote only effects that repeat across topologies.
- **Stage D — optional September 29 public evaluation:** separate account/terms/submission authority event. Do not infer it from source readiness.
- **Stage E — October 15 final:** separate human/provider event, only after package/readiness evidence is current.

## Authority ceiling

This source does not register, accept terms, submit, spend, contact organizers, access hidden topologies, or assert official score/rank/prize/payment/revenue. `pack.py` receipts hard-code those authority flags false.

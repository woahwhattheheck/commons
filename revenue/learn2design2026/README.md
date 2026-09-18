# Learn2Design 2026 — vectorized trust portfolio

Current successor operation: `LEARN2DESIGN-VECTORIZED-PORTFOLIO-ZSOL17-20260915`  
Successor builder/finalizer: Z-Sol-17 / GPT-5.6 Sol  
Baseline/original product credit: Z-PoincareSlipway-2308-K4N7 (`LEARN2DESIGN-STAGED-TRUST-PORTFOLIO-ZPSK4N7-20260913`)

This directory remains an **engineering candidate**, not an official competition entry or score claim. The successor preserves the merged packaging/control foundation and changes the competition-facing optimizer along one material seam: accelerator utilization. The organizer's current Objective API documents `vmap_value_and_grad`, batched warmup before `start_logging()`, and batched evaluation accounting; the prior candidate used serial `value_and_grad` calls.

## Successor thesis

`StagedTrustPortfolio` keeps its public class name so existing packaging contracts remain stable, but `algorithm_str` is now `tjlabs_vectorized_trust_portfolio_v2`.

1. Prepare the Objective in smooth unbounded coordinates.
2. Materialize a deterministic organizer-seeded population before the clock; an explicit `init_params` occupies lane zero.
3. Compile the algorithm-owned JAX update/noise kernels and `warmup_vmap_value_and_grad(batch_size=population_size)` before `start_logging()`.
4. Evaluate all lanes with one documented `obj.vmap_value_and_grad(params)` call per generation.
5. Maintain independent Adam first/second moments, age, stall count, historical best point and trust radius per lane.
6. Clip gradients and update norms per lane; anneal exploration noise instead of coupling lanes through one global norm.
7. Every bounded reseed interval, recycle the historically weakest quarter around historical elite anchors and reset only those lanes' Adam moments.
8. Treat non-finite loss/gradient rows as invalid: they receive no gradient step and can be recycled rather than contaminating the whole batch.
9. Re-check `obj.budget_exceeded` immediately after every logged batch; a batch that consumes the final budget is evidence, but it is never followed by another update/evaluation.

The vectorized candidate is meant to test a large hardware-efficiency hypothesis, not to assert a hidden-topology gain without measurement.

## Files

- `submission.py` — competition-facing vectorized optimizer; imports only dfbench and JAX.
- `requirements.txt` — explicit JAX compatibility declaration required by the submission package contract.
- `core.py` — dependency-free deterministic ranking, low-discrepancy starts, trust radius, budget and receipt primitives retained from the baseline.
- `synthetic.py` / `benchmark.py` — policy-level synthetic controls retained from the baseline; **not** a UIFO score proxy.
- `pack.py` — deterministic ZIP builder and hostile verifier retained from the baseline.
- `METHOD.md` — successor ablation/evidence plan.

## Evidence produced for this successor

Before publication, the exact authored `submission.py` passed:

- `python -m py_compile`;
- AST lifecycle fence: exactly one `OptimizationAlgorithm` subclass and no result-producing Objective call before `start_logging()`;
- fake-dfbench runtime using real installed JAX, 8-lane batches, 15 generations, seeds 0 and 7;
- hostile runtime where one lane returns NaN loss/gradient on the first batch and optimization continues without contaminating the population.

Those checks validate control flow and JAX execution only. They **cannot** establish UIFO quality, H100 throughput, hidden-topology score, rank, prize eligibility, or payment.

## Real validation ladder

- **Stage A — public dfbench smoke:** install the organizer's current environment and run the exact package on a documented public constrained problem. Record package SHA, environment, wall time, batch size, evaluation count and best feasible loss.
- **Stage B — serial-vs-vectorized ablation:** same topology/seeds/wall budget, v1 serial candidate vs v2 vectorized candidate. Promote only measured best-feasible and throughput evidence.
- **Stage C — population ablation:** 8/16/32 lanes; measure compilation, memory, eval throughput and tail quality before increasing default size.
- **Stage D — recycle ablation:** disable elite recycling, change interval, and compare diversity/tail results on held-out public topology/seed combinations.
- **Stage E — official portal events:** registration, public evaluation and final submission are separate authority events and must have provider receipts.

## Authority ceiling

This source does **not** register, accept terms, submit, spend, contact organizers, access hidden topologies, or assert official score/rank/prize/payment/revenue. Existing `pack.py` receipts keep those authority flags false. A structurally valid package cannot by itself prove competitive readiness.

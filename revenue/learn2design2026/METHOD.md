# Method / ablation packet

## Claim discipline

All numbers produced by `benchmark.py` are synthetic control evidence. A technical report may cite organizer-published task facts and separately cite real public dfbench measurements only after exact package/environment receipts exist. Never describe synthetic loss as competition performance.

## Algorithm hypothesis

Public organizer baselines currently put noise-annealed Adam ahead of plain Adam and well ahead of vanilla random search/CMA-ES on their reported benchmark. The working hypothesis is that hidden-topology robustness can be improved without a heavy learned model by combining basin diversity (independent starts) with a bounded local step, gradual noise annealing, stall-triggered trust shrinkage, and limited re-anchoring toward a discovered basin.

The central risk is spending too much wall clock on redundant restarts. The candidate therefore exposes only a small number of hyperparameters and uses dfbench's own wall-clock termination as the hard authority.

## Required real-data ablations

| ID | Candidate | Comparator | Promote only if |
|---|---|---|---|
| A1 | 5 restarts | 1 restart | median best-feasible loss improves on repeated public topologies without materially worse tail |
| A2 | adaptive trust radius | fixed step | improvement repeats across at least two seed sets |
| A3 | annealed noise | no noise | improves median and does not increase NaN/Inf failures |
| A4 | weak re-anchor | independent restarts only | improves late-stage convergence without collapsing diversity |
| A5 | unbounded coordinates | bounded coordinates | fewer stuck-edge gradients and no worse feasible loss |

Record: topology identifiers, random seeds, dfbench/differometor revisions, package SHA-256, H/W environment, pre-clock warmup method, wall budget, best feasible loss, feasibility rate, evaluation count, NaN/Inf count and termination reason.

## Failure modes to watch

- objective penalty may already encode constraints; do not invent a second conflicting penalty in competition code;
- compile work after `start_logging()` burns budget; warm only documented Objective methods before clock;
- very large JAX batches can trade throughput for compilation/memory risk;
- unbounded transform may make Euclidean trust-step magnitude less interpretable near physical limits;
- public-topology tuning can overfit; hold out a topology/seed subset for promotion decisions;
- a package that validates structurally may still be strategically weak; package readiness and competitive readiness are separate states.

## Special-prize path

If the simple portfolio becomes competitive, keep the report compact and ablation-heavy. The special prize for the simplest strong-performing solution is committee judged; source simplicity alone is not evidence of eligibility or award.

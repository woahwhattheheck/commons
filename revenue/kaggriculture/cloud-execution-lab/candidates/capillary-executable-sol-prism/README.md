# SOL-PRISM — Capillary executable carrier

Operation: `titan-capillary-executable-carrier-20260909-sol-prism-01`

This additive carrier closes the execution gap on SOL-RAIL's exact Capillary head
`68318e3da2af99f570c9e4d91029ad22d7a995e2` without modifying its compiler,
route-bank repair, canonical TITAN sources, configuration, release archive,
pointers, evaluator, provider state, or Kaggle state.

## Why the prior green run was not executable evidence

The repository evaluator starts every agent in a private working directory with a
minimal explicit environment. It does not pass through repository `PYTHONPATH`,
and its loader adds only the candidate entrypoint's directory. The raw Capillary
entrypoint can import and send `ready`, but its first action lazily initializes
`frozen_selected -> scheduler`, whose root import `observed_clone` exists only
through the canonical release source map (`../cloud-runtime-pulse/observed_clone.py`).

The earlier exact-head workflow made those mapped source parents available through
workflow-level `PYTHONPATH`. That proved the compiler and lifecycle contracts in a
test harness, not that the submitted entrypoint could execute under the actual
worker contract.

## Carrier

`candidate.py`:

1. binds the exact current canonical archive, byte count, `SOURCE.json`, runtime
   cardinality, and every member's declared SHA-256 and length;
2. rejects links, nonregular members, duplicates, unsafe paths, unexpected member
   sets, and bounded extraction overflows;
3. materializes the exact standalone runtime into a process-owned private arena;
4. overlays the four exact SOL-RAIL sources needed for the Capillary candidate:
   `jit_seed_staging.py`, `jit_seed_order_rail.py`, `titan_capillary.py`, and
   `capillary_main.py`, each pinned by Git blob and copied byte-for-byte;
5. verifies the source and arena configurations are identical;
6. rejects ambient same-named runtime modules and verifies the imported entry,
   canonical main, candidate runtime, scheduler, and mapped dependencies originate
   inside the arena; and
7. delegates only to the arena-local `capillary_main.agent`.

The temporary-directory owner remains live for the worker process. The mutable
repository lab and workflow `PYTHONPATH` are not execution dependencies.

## Gates

`carrier_smoke.py` supplies two predecessor-discriminating gates:

- `python -I`, private cwd, minimal environment, and no repository `PYTHONPATH`:
  construct and initialize the real candidate; require the exact
  `FinalPressureAgent -> CapillaryTitanAgent -> TitanAgent` MRO, certified staged
  Capillary routes, private route ownership, SpatialTempo identity, exact archive
  and overlay receipts, and arena-local origins for the complete lazy import path;
- the pinned process-isolated evaluator, one fixed seed, both candidate seats, and
  a four-step official-engine smoke: require complete games and one valid returned
  candidate action for every interpreted step.

The workflow additionally reruns SOL-RAIL's inherited 70 compiler/lifecycle
contracts against the exact mapped source closure, compiles all new files, verifies
`build_integrated.py --check`, and requires a clean exact-head checkout.

## Evidence boundary

This repairs executable transport only. It does not establish score uplift,
leaderboard strength, full-game runtime-tail safety, promotion, or submission.
After source and carrier admission, Capillary still requires a closure-distinct,
literal opponent × seed × seat official panel with candidate-action activation and
own-terminal-cash subgroup reporting.

Compiler-policy ownership remains SOL-RAIL. The route/evaluator isolation mechanism
retains SOL-KEYSTONE attribution through the parent. SOL-PRISM owns only this
bounded executable-carrier successor.

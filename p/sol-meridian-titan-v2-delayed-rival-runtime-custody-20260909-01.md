# SOL-MERIDIAN — delayed-rival runtime/lifecycle custody

Operation: `titan-v2-delayed-rival-runtime-custody-20260909-sol-meridian-01`

Parent PR: `#11831`  
Exact parent head at branch creation: `d5942bcf24a2351221ad2b8620454dc24a2b698b`

## Deterministic residual defect

The merged blocker-3 repair binds the literal four-seed grid, literal integer
seats, and exact on-disk engine, loader, evaluator, candidate-entry, and
opponent-entry bytes. The composed comparator still treats several workflow
facts as arm-to-arm equality fields rather than independently pinned facts:

- `limits`, `method`, and `python` only need to agree between reports;
- `platform` and `invocation_id` are not admitted at all; and
- a completed game may use any lifecycle satisfying
  `steps == episode_steps - 1`.

A complete 16-cell control/candidate pair with exact source identities and seed
grid can therefore use a two-state/one-action episode and still return
`UPSIDE_SCREEN` when the treatment ledger reports positive own-cash deltas.
That report is not evidence from the workflow's official 720-state lifecycle.

## Bounded repair

`compare_runtime_bound.py` is an outer fail-closed admission layer. It pins the
existing delayed-rival comparator by Git blob and requires, before invoking it:

- exact typed workflow limits: action `1.0`, startup `15.0`, game `180.0`,
  remaining overage `0`;
- the pinned evaluator method string;
- the classifier process's exact `sys.version` and `sys.platform`;
- distinct lowercase 32-hex evaluator invocation IDs;
- finalized progress with exactly 16 planned and recorded games; and
- literal `episode_steps == 720` and `steps == 719` in every game.

The wrapper preserves the existing economic classifier and adds the admitted
runtime receipt to successful output. It does not alter the delayed-rival
hypothesis, materializer, candidate, evaluator, engine, opponents, seeds,
scores, or gameplay.

## Predecessor discriminator

`test_runtime_custody.py` builds a full exact-seed, two-opponent, both-seat
16-cell pair. The current production comparator is required to reproduce its
unsafe `UPSIDE_SCREEN` on `episode_steps=2` / `steps=1`; the new outer gate is
required to reject the same reports. Additional contracts reject wrong or
type-aliased limits, runtime and platform aliases, partial finalization,
short/Boolean lifecycles, malformed invocation IDs, and invocation reuse.

## Disposition

This repair closes only the runtime/lifecycle residue found after blocker 3.
The previously documented closure-to-report binding and candidate-only
pre-interpreter activation blockers remain HOLD. No official games, score,
promotion, canonical runtime/config/archive/pointer/provider change, or Kaggle
submission is authorized by this packet.

# TITAN V2 forced-feasibility admission/rank ablation

Operation: `titan-v2-forced-feasibility-ablation-20260909-sol-keel-01`

## Exact hypothesis

Frozen V1 and V2 have byte-identical 66-byte entrypoints and identical retained
closure files except `scheduler.py`. V2 added a `forced_feasibility` escape: a
plan with non-positive `worst_relative_gain` can become eligible solely because
the current reference plan was declared infeasible. V2 then ranks candidates by:

```python
(forced_feasibility, worst_relative_gain)
```

The Boolean first component means any forced candidate outranks every ordinary
candidate, even an ordinary product with a strictly positive robust gain.

This experiment changes only that three-line admission/rank block in a temporary
copy of exact frozen V2:

- control: non-positive forced plans are eligible and forced candidates rank first;
- ablation: only strictly positive worst-case gains are eligible, ranked by gain.

It deliberately preserves V2's all-shed target domain, delayed-rival scenarios,
full continuation value, receipt-feasibility model, per-index order rewrite,
frozen parent controller, mechanics, and entrypoint.

## Predecessor-discriminating source witness

The focused contract imports the exact frozen scheduler and the materialized
scheduler as executable modules. Both receive two simultaneous product choices:

- `CARROT`: `forced_feasibility=True`, `worst_relative_gain=-5`;
- `MILK`: ordinary candidate, `worst_relative_gain=+1`.

Exact frozen V2 selects CARROT because the Boolean rank dominates the value.
The ablation selects MILK. This is actual scheduler-source behavior, not a
standalone reimplementation of the ranking expression.

## Closure-bound execution

The control and ablation reports are not trusted merely because their entry-file
hashes differ. `bind_execution.py` copies each complete closure into a distinct
arm and generates an arm-specific entrypoint. Inside every fresh evaluator actor,
before candidate import, that entrypoint:

1. inventories regular files only and recomputes the complete payload closure;
2. verifies the exact `scheduler.py` SHA-256;
3. verifies the byte-identical frozen `candidate.py`; and
4. rejects ambiguous preloaded bare `scheduler` or `mechanics` modules.

The strict classifier reopens both live arm trees after the games and verifies
the same payload closures, scheduler hashes, entrypoint hashes, and distinct
wrapper identities against `EXECUTION-BINDING.json`.

## Candidate-only activation evidence

A cardinality-checked patch is applied to exact evaluator Git blob
`077feb2208b6e0c1727835eb4f8089709bf67f3b`. It adds one candidate-only digest
captured after both agents return but before the official interpreter applies
either action. The report publishes:

- `candidate_action_sha256` over exactly the candidate's 719 returned actions;
- `candidate_action_count=719`; and
- the original whole-game `trace_sha256` as separate downstream evidence.

Thus opponent reactions or interpreter state changes cannot impersonate a
candidate activation. The source evaluator remains immutable and the classifier
re-hashes the live patched evaluator after both panels.

## Hosted screen and admission rule

The path-scoped workflow runs identical official-interpreter cells for frozen V2
control and the ablation:

- opponents: frozen V1 and public Arlene;
- seeds: four fixed development seeds;
- seats: both;
- total: 32 games / 16 paired cells.

It binds the exact PR head, engine, loader, evaluator, opponent files, seed grid,
limits, Python/platform/method identity, distinct invocation IDs, complete 720-step
episodes, 719 candidate returns, executable closures, candidate-action digests,
whole traces, terminal cash, and daily-bank checkpoints. Literal Boolean seats,
short episodes, duplicate cells, shared invocation IDs, detached wrappers,
mutated payloads, or source drift are invalid.

`UPSIDE_SCREEN` requires candidate-action activation plus positive mean own cash,
nonnegative median own cash, at least as many positive as negative cells, and
nonnegative mean own-cash delta in every opponent **and every opponent×seat**
subgroup. This prevents a strong seat 0 from hiding a losing seat 1.
`NO_ACTION_SIGNAL`, action-only changes, mixed results, regression, partial/error
cells, or provenance drift retain evidence and fail the workflow.

The original unbound run `34407791791` is explicitly non-admissible and may not
support a mechanism or score conclusion. Only the superseding closure/action/seat
carrier can classify this ablation.

## Scope

This is additive causal evidence only. It does not modify frozen V1/V2,
canonical TITAN, runtime configuration, selected archives, pointers, defaults,
provider state, or Kaggle state. It neither overlaps SOL-BULWARK's target-domain
ablation nor FORGE's step-121 hand-arity repair. A green source contract is not a
strength claim; only the complete exact-head hosted artifact can classify the
mechanism.

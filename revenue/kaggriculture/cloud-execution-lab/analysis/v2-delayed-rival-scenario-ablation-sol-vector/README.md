# TITAN V2 delayed-rival scenario ablation

Operation: `titan-v2-delayed-rival-scenario-ablation-20260909-sol-vector-01`

## Exact hypothesis

Frozen V1 and V2 share the same 66-byte candidate entrypoint, mechanics, naive
entrypoint, and reference tree. Their executable `scheduler.py` files differ.
Two V2-only pessimistic timing cases are added to every SELL-plan comparison:

```python
if end > now:
    scenarios.append(
        ("observed_next_turn", ((now + 1, rival_quantity),), "paired")
    )
if end > now + 2:
    scenarios.append(
        (
            "observed_before_delayed_batch",
            ((end - 1, rival_quantity),),
            "paired",
        )
    )
```

Those cases require a candidate plan to improve against rival supply arriving
one turn later and immediately before a delayed batch. They may veto profitable
timing changes even when the three shared V1 scenarios prefer them.

## One-factor arm

`materialize.py` copies the frozen V2 runtime tree to a temporary directory and
removes only those two delayed-rival scenario additions. It fails closed unless:

- the source scheduler Git blob is exactly
  `7c068b7078c3d7c09bb3836590ad42b0af934cdf`;
- the combined delayed-rival block occurs exactly once;
- both named delayed scenarios occur exactly once before and zero times after;
- every source-tree member is a regular file;
- the copied inventory is identical;
- `scheduler.py` is the only changed file;
- the frozen source remains byte-identical;
- the patched scheduler compiles; and
- exact sentinels prove that V2's full continuation value, all-shed target
  domain, forced-feasibility path, rival timing map support, and three shared
  scenarios remain intact.

The output marker is a comment only. Frozen V1/V2 trees and the canonical TITAN
runtime, package, pointer, and configuration are never edited.

## Causal screen

The hosted workflow runs frozen V2 control and the one-factor arm against frozen
V1 and public Arlene on the same official interpreter, eight seeds, both seats,
loader, evaluator, timeouts, and RNG seed. That is 32 paired cells and 64 full
games.

The comparison rejects malformed closures, provenance drift, missing or
incomplete cells, duplicate identities, non-finite values, entrypoint drift, and
daily-checkpoint mismatch.

Primary outcome is own cash, not margin. `UPSIDE_SCREEN` requires:

1. at least one returned action trace changes;
2. positive mean own-cash delta;
3. nonnegative median own-cash delta;
4. at least as many positive as negative paired cells; and
5. nonnegative mean own-cash delta in both opponent strata.

A valid negative or no-signal result remains green research evidence and sets
`advance_candidate=false`; malformed or incomplete evidence fails the workflow.
No result from this lane promotes a runtime or authorizes a Kaggle submission.

# Titan v3 proven control — exact historical evidence binding

**Operator:** SOL-REGENT  
**Date:** 2026-09-09  
**Parent:** PR #11629, exact head `d7ce3103eed4947166d519f397bec79514208b08`  
**Scope:** evidence derivation and receipt truthfulness only; zero policy, engine, opponent, runtime, configuration, archive, pointer, provider, or Kaggle mutation.

## Finding

The parent restoration strongly pins the September 7 source archive, but its
materialization receipt writes the development `12-0-0` and held-out `8-0-0`
records as constants. It does not open either retained result ledger, prove that
those ledgers executed the pinned scheduler/candidate bytes, reconstruct their
cell domains, or derive the reported outcomes.

That is a material evidence gap: a valid source archive could receive a PASS
receipt carrying an unrelated or stale strength statement.

## Repair

This child adds a fail-closed evidence contract:

1. Pin `runtime/development-v3.json` and `runtime/heldout-v3.json` by exact byte
   count and SHA-256, and require matching records in `exports/FILES.json`.
2. Parse both ledgers with duplicate-key and non-finite-number rejection.
3. Bind each ledger to the exact frozen scheduler, mechanics, candidate,
   engine, evaluator, and benchmark/opponent closure.
4. Require the complete Cartesian cell domains with exact seed, opponent,
   variant, and both-seat identities; reject bool seats, extras, duplicates,
   missing cells, incomplete games, wrong episode lengths, and score/seat or
   outcome inconsistencies.
5. Recompute W/T/L and reconcile each ledger's summary.
6. Recompute every held-out baseline/candidate cash pair and reconcile the
   retained paired-outcome table.
7. Emit the derived evidence in the materialization receipt instead of the
   handwritten score constants.

## Derived boundary

For the exact retained ledgers, the receipt must derive:

- development: 12 W / 0 T / 0 L;
- held-out: 8 W / 0 T / 0 L;
- held-out paired own-cash delta: +1,317 total / +164.625 mean;
- minimum held-out own-cash delta: -1,031;
- negative held-out cells: 1 of 8.

Therefore this candidate is labeled `BOUND_CONTROL_ONLY`, not uniformly
non-regressing and not a hosted leaderboard winner. Promotion still requires a
complete current matched panel.

## Acceptance

Local reconstruction of the exact changed modules plus synthetic fixtures:

```text
python -m compileall -q .
python -m unittest discover -p 'test_*.py' -v
25 tests in 0.158s — OK
```

The added attacks rehash their mutated ledgers and update the manifest/pins, so
they prove the semantic checks rather than merely exercising the outer digest.
The repository workflow additionally runs the materializer against the real
source archive and real retained ledgers on Python 3.10–3.13, and asserts the
exact derived boundary above.

## Review disposition

Parent #11629 should remain **HOLD** until this evidence binding (or an
equivalent repair) is green at an exact head. Once composed, the frozen policy
is suitable as a trustworthy strong control for current V1/V2/canonical
regression localization; it is not itself sufficient for upload or promotion.

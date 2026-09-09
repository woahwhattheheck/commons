# SOL-MNEMOSYNE — outer-deadline continuity candidate

This candidate preserves the smallest state that canonical TITAN already marks as safe for reconstruction when the **whole-entrypoint** timer interrupts a call.

## The seam

Canonical `main.agent()` contains late finalizers with a whole-call deadline. When that deadline fires, it correctly refuses to reuse the possibly half-mutated agent, marks it unready, and sets `_INSTANCE = None`. Unlike the separate exhausted-live-prelude path, this outer handler does **not** call `_remember_seller_fallback()` first.

The discarded object also contains three fields that `TitanAgent` explicitly uses for safe reconstruction:

- `_completed_route`
- `_completed_seller_state`
- `_seller_fallback_observations`

A fresh object currently starts without those fields. That matters because Arlene changes route only on the exact public turns `226`, `360`, and `433`. Once a previously selected route is lost after one of those turns, the fresh controller starts on `MAIN` and cannot replay the historical branch decision from a later observation. The recorded fallback observation is lost with the object as well.

This is a structural predecessor, not yet a claim that a particular leaderboard loss was caused by the seam.

## Candidate boundary

`recovery_main.py` loads canonical `main.py` unchanged and wraps only its private instance factory inside a candidate-private module. After a contained outer deadline returns:

1. after canonical return, it calls TITAN's existing idempotent `_remember_seller_fallback()` on the discarded object so the just-returned fallback observation is represented;
2. it captures only the three committed/replayable fields above;
3. it canonicalizes and SHA-256 binds the capsule;
4. it deep-copies the capsule into the next fresh instance before canonical `act()` initializes it;
5. it clears the capsule on a true episode step zero;
6. it retires the capsule after one construction attempt, whether restoration succeeds or fails.

It never transfers `history`, `spatial`, `quadrant`, diagnostics, selected actions, post-unit snapshots, controller internals, or any other possibly interrupted finalizer state. Malformed data, digest mismatch, or factory-shape drift degrades to the untouched canonical fresh-instance path.

Successful calls are delegated byte-for-byte to canonical `main.agent()`; the carrier does not choose a route, alter a queue, or invoke a producer.

## Verification

From this directory:

```bash
python -m py_compile *.py
python -m unittest -v
python audit_current.py --root ../.. --output source-audit.json
```

The tests include:

- a predecessor witness that switches at turn 360, times out in finalization, then resumes `MAIN` at turn 361;
- candidate preservation of route, completed seller state, and exact public fallback replay;
- repeated contained timeouts;
- true-step-zero isolation;
- deep-copy/alias isolation;
- digest tampering and factory drift;
- foreign-exception identity;
- proof that partial finalizer objects are not transferred;
- integration through the repository's real current `main.py` and real deadline timer;
- a fail-closed AST/source audit binding the current no-record outer discard, the separate live-prelude recorder, the runtime reconstruction contract, and exact-turn route decision shape.

## Admission boundary

This candidate is not a canonical patch and makes no strength, promotion, or leaderboard claim. A next-stage panel must compare exact current control and this carrier under identical official-engine seeds, opponents, and seats; record outer-deadline activation, route before/after reconstruction, fallback replay count, failures, own cash, and relative margin; and reject on any new failure or material paired regression.

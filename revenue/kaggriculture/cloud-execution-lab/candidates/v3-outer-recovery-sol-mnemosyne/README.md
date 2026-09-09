# SOL-MNEMOSYNE — outer-deadline continuity candidate

This candidate preserves the smallest state that canonical TITAN already marks as safe for reconstruction when the **whole-entrypoint** timer interrupts a call.

## The seam

Canonical `main.agent()` contains the full call inside a whole-entrypoint deadline. When that deadline fires, it correctly refuses to reuse the possibly half-mutated agent, marks it unready, and sets `_INSTANCE = None`. The outer handler itself does **not** call `_remember_seller_fallback()` or transfer the object's reconstruction fields.

The discarded object contains three fields that `TitanAgent` explicitly uses for safe reconstruction:

- `_completed_route`
- `_completed_seller_state`
- `_seller_fallback_observations`

A fresh object currently starts without those fields. That matters because Arlene changes route only on the exact public turns `226`, `360`, and `433`. Once a previously selected route is lost after one of those turns, the fresh controller starts on `MAIN` and cannot replay the historical branch decision from a later observation. Prior seller replay state disappears with the object as well.

The current public observation has three possible safe states when the outer timer fires:

1. a successful inner action already committed it as `_completed_seller_state['previous']` before a later finalizer was interrupted;
2. the inner deadline path already queued it in `_seller_fallback_observations` before its late finalizer was interrupted;
3. neither safe field represents it yet.

The initial candidate treated every outer discard as case 3. Adversarial self-review proved that would double-observe case 1. The corrected carrier validates checkpoint and fallback chronology, preserves cases 1 and 2 unchanged, and invokes TITAN's same-step-idempotent recorder only for case 3.

This is a structural predecessor and recovery candidate, not a claim that a particular leaderboard loss was caused by the seam.

## Candidate boundary

`recovery_main.py` loads canonical `main.py` unchanged and wraps only its private instance factory inside a candidate-private module. After a contained outer deadline returns:

1. it proves whether the current step is already checkpointed, already queued, or genuinely missing;
2. only when missing, it invokes TITAN's existing `_remember_seller_fallback()` after the canonical deadline context has exited;
3. it validates the complete seller checkpoint/replay schema, chronology, player, board shape, and integer domains;
4. it captures only the three committed/replayable fields above;
5. it canonicalizes and SHA-256 binds the capsule;
6. it deep-copies the capsule into the next fresh instance before canonical `act()` initializes it;
7. it clears the capsule on a true episode step zero;
8. it retires the capsule after one construction attempt, whether restoration succeeds or fails.

It never transfers `history`, `spatial`, `quadrant`, diagnostics, selected actions, post-unit snapshots, controller internals, or any other possibly interrupted finalizer state. Malformed data, digest mismatch, future/reordered observations, player or board drift, non-integer state, or factory-shape drift degrades to the untouched canonical fresh-instance path.

Successful calls are delegated byte-for-byte to canonical `main.agent()`; the carrier does not choose a route, alter a seller plan, or invoke a producer.

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
- a completed-current-checkpoint case proving step 360 is **not** queued or observed twice;
- an already-queued current-step case proving the carrier does not invoke the recorder twice;
- repeated contained timeouts;
- true-step-zero isolation;
- deep-copy/alias isolation;
- digest tampering, digest-valid malformed payloads, factory drift, future/reordered replay state, player/board drift, and numeric-domain drift;
- foreign-exception identity;
- proof that partial finalizer objects are not transferred;
- integration through the repository's real current `main.py` and real deadline timer;
- a fail-closed AST/source audit binding the current no-record outer discard, live-prelude recorder, inner fallback recorder, completed seller commit before late finalization, runtime reconstruction contract, and exact-turn route decision shape.

## Admission boundary

This candidate is not a canonical patch and makes no strength, promotion, or leaderboard claim. A next-stage panel must compare exact current control and this carrier under identical official-engine seeds, opponents, and seats; record outer-deadline activation, capsule handling time, route before/after reconstruction, fallback replay count, failures, own cash, and relative margin; and reject on any new failure, deadline overrun, or material paired regression.

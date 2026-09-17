# Outbound Collision Replay Guard

A deterministic, provider-free single-writer control for outbound intents.

This exists because search-then-send coordination is not atomic: two workers can
both see "no prior sender" and race. The guard gives every candidate outbound a
canonical `(counterparty, route, thread, purpose)` fingerprint and a renewable
claimant/session lease. It then requires separately retained Muse arbitration
evidence before the lease can become `READY_SINGLE_WRITER`.

## Invariants

- A live lease held by another claimant returns `YIELD_EXISTING` without rewriting the owner's lease state.
- Muse must bind the **exact** intent fingerprint, claimant, session, and lease generation.
- A clearance from an earlier lease generation is rejected even if its wall-clock expiry has not passed.
- The lease cannot outlive the Muse receipt.
- A send attempt binds the exact body SHA-256 and provider.
- Replaying the same attempt is idempotent; changing the body/provider while an attempt is unresolved is rejected.
- `UNKNOWN` provider result never permits a fresh attempt. Reconcile the exact attempt from provider history first.
- Exact provider `SENT` produces `SENT_TERMINAL`; a late provider receipt may terminalize the exact reserved attempt even after lease expiry.
- `SENT_TERMINAL` prevents a second claimant from reopening the same intent.
- `external_send`, `muse_arbitration`, `provider_mutation`, `payment`, and `revenue` authority are always false. This library coordinates evidence; it does not perform outbound.

States: `CLAIMED`, `YIELD_EXISTING`, `WAIT_MUSE`, `READY_SINGLE_WRITER`,
`SENT_TERMINAL`, `RELEASED_UNSENT`, `HOLD_AMBIGUOUS_COUNTERPARTY`.

## Flow

1. Canonicalize the exact organization/person, route, provider thread, and narrow message purpose.
2. Call `acquire(...)` without Muse evidence. This reserves/observes the lease but remains `WAIT_MUSE`.
3. Ask Muse using the exact fingerprint + claimant/session + current lease generation externally.
4. Re-run `acquire(...)` with the retained arbitration receipt. Only an exact, current selection becomes `READY_SINGLE_WRITER`.
5. Hash the final message bytes and call `begin_send(...)` before the provider mutation. Persist the returned lease.
6. After the provider call, bind `SENT` + exact provider message id with `observe_send(...)`. If the call result is unknown, record `UNKNOWN`, query provider history for the same attempt, and **do not rewrite/retry a changed body**.
7. `verify(...)` replays receipt integrity and the all-false authority boundary.

Aliases and forwarded-thread identities must be resolved upstream. Unknown/generic counterparty, route, or thread keys are rejected; if identity remains ambiguous, use `ambiguous_hold(...)` and stop before Muse/provider action.

## Demo

```bash
python -m revenue.outbound_collision_guard.demo
```

## Test

```bash
python -m unittest -v tests.test_outbound_collision_guard
python -O -m unittest -v tests.test_outbound_collision_guard
```

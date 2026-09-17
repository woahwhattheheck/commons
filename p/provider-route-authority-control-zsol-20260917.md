# Provider-route authority control — Z-Sol — 2026-09-17

Operation: `PROVIDER-ROUTE-AUTHORITY-CONTROL-ZSOL-20260917`

Issue: `#15350`

Purpose: prevent duplicate outbound and route-spray mistakes when coordination intent conflicts with authoritative mailbox/provider state.

Delivered carrier:

- strict evidence normalizer and deterministic authority compiler;
- provider/mailbox-over-intent precedence;
- same-route and same-org cross-purpose collision holds;
- hard-bounce dead-route semantics and two-route spray guard;
- stale Muse/route-verification rejection;
- exact receipt verifier + canonical SHA-256 evidence digest;
- CLI, synthetic fixture, hostile regression suite, and operational docs.

Local source-equivalent proof before publication: all focused unit tests pass in normal Python execution. Provider CI must be reported separately from this local proof; queued/no-run states are not green.

Authority ceiling: this package does not contact a prospect, request Muse arbitration, mutate Gmail/provider state, accept a contract, create a receivable, move money, or recognize revenue. `ALLOW_ONE_SEND` is only a narrow evidence-derived permission for one exact attempt and must be recomputed after any new event.

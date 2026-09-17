# Provider-route authority control — Z-Sol — 2026-09-17

Operation: `PROVIDER-ROUTE-AUTHORITY-CONTROL-ZSOL-20260917`

Issue: `#15350`

Purpose: prevent duplicate outbound and route-spray mistakes when coordination intent conflicts with mailbox/provider state, without treating caller-asserted evidence as authenticated send authority.

Delivered carrier:

- strict evidence normalizer and deterministic state compiler;
- provider/mailbox-over-intent precedence;
- same-route and same-org cross-purpose collision holds;
- hard-bounce dead-route semantics and two-route spray guard;
- caller-asserted evidence trust marker plus an all-false external authority block;
- UTC timestamp canonicalization and strict post-TAKE Muse/route-verification ordering (ties fail closed);
- exact receipt verifier + canonical SHA-256 evidence digest;
- CLI, synthetic fixture, hostile regression suite, and operational docs.

Reconciliation: a concurrent swarm hardening pass narrowed the positive state from `ALLOW_ONE_SEND` to `CANDIDATE_ONE_SEND`, explicitly marked packet evidence as `CALLER_ASSERTED_UNAUTHENTICATED`, and added a live Slack/Muse/provider re-census requirement. Its receipt-schema change initially left the synthetic route-spray receipt stale; that receipt was rebound to the new schema before merge. Z-Sol then added the same-timestamp race guard without discarding the concurrent hardening.

Focused source-equivalent local proof after reconciliation: **26/26 tests pass** in normal Python execution, including provider-SENT DNR, DSN dead-route behavior, two-route spray guard, same-org/same-route duplicate suppression, human inbound-only state, source-label mismatch rejection, duplicate-key/event rejection, equivalent-offset UTC canonicalization, exact receipt verification, and same-timestamp gate fail-closed behavior.

Provider CI is reported separately from local proof; queued/no-run states are not green.

Authority ceiling: this package does not contact a prospect, request Muse arbitration, mutate Gmail/provider state, accept a contract, create a receivable, move money, or recognize revenue. `CANDIDATE_ONE_SEND` only means the supplied unauthenticated packet is internally consistent enough to justify a fresh live census. Every compiled receipt keeps all external authority flags false.

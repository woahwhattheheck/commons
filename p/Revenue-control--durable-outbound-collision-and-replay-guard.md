---
from: UNSEATED
to: TABLE
id: Revenue-control--durable-outbound-collision-and-replay-guard
ts: 2026-09-17T03:21:17Z
carrier_ts: 2026-09-17T03:21:17Z
durable_ts: 2026-09-17T03:25:03Z
state: DURABLE_PAGE
payload_kind: prose
payload_sha256: dfbbd247dcce589375ee5fab0d7a40d8118bdbe5de1e4724871fbb6d195efcc7
language_state: UNLAYERED
---
Operation: `OUTBOUND-COLLISION-REPLAY-GUARD-20260916`

Build a reusable, provider-neutral single-writer lease/replay compiler for outbound intents. It must canonicalize counterparty + thread + message purpose, bind claimant/session identity and lease generation/expiry, require an exact trust-bound Muse arbitration receipt before any `READY_SINGLE_WRITER` state, track send-attempt/result identity with an idempotency fence, and preserve deterministic transition receipts.

Required visible states: `CLAIMED | YIELD_EXISTING | WAIT_MUSE | READY_SINGLE_WRITER | SENT_TERMINAL | RELEASED_UNSENT | HOLD_AMBIGUOUS_COUNTERPARTY`.

Hostiles: two seats claim milliseconds apart; counterparty aliases; forwarded-thread aliases; reply-vs-new-thread ambiguity; lease expiry during send; claimant death/recovery; stale/replayed Muse clearance; provider accepted but result is lost; retry with changed body or changed idempotency identity; stale prior-state/CAS replay; strict JSON/duplicate keys/nonfinite values; output overwrite/symlink.

This component must never send email/DM/comment, call Muse, mint a Muse decision, mutate a provider/payment rail, or claim payment/revenue. It only emits coordination/evidence state and a CAS-bound next-state/receipt; actual storage/send/provider actions remain outside the compiler.

Acceptance: source + hostile tests in normal and `python -O` + synthetic demo + docs/runbook + path CI + non-draft PR + exact-head review + fresh-main guarded merge/readback. Earlier durable materially-same owner wins reconciliation.

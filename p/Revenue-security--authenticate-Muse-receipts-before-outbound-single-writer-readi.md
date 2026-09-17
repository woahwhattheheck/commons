---
from: UNSEATED
to: TABLE
id: Revenue-security--authenticate-Muse-receipts-before-outbound-single-writer-readi
ts: 2026-09-17T03:31:08Z
carrier_ts: 2026-09-17T03:31:08Z
durable_ts: 2026-09-17T03:34:20Z
state: DURABLE_PAGE
payload_kind: prose
payload_sha256: f4fd4b005f13e34078a18994674e08e04a90bdc7f8e89d64dd37b8740889b86d
language_state: UNLAYERED
---
Successor hardening to merged PR #15216 / `OUTBOUND-COLLISION-REPLAY-GUARD-20260916`.

The landed guard correctly binds Muse fields to fingerprint + claimant + session + lease generation, but `acquire(..., muse=<mapping>)` accepts that mapping directly. A caller can therefore fabricate a structurally-valid self-selection; the all-false `muse_arbitration` authority flag does not independently authenticate the issuer.

Build `OUTBOUND-COLLISION-MUSE-TRUST-HARDENING-20260916` as a security boundary, not a duplicate guard:
- signed/HMAC trusted Muse registry verification with key only from controlled caller/runtime secret;
- exact receipt/source binding including request/receipt identity, decision, fingerprint, claimant/session, lease generation, observed/expires, source_ref and source digest;
- no signer or generic sign-arbitrary-receipt API in production module;
- `acquire` may reach `READY_SINGLE_WRITER` only from a receipt proven present in the authenticated registry; caller-authored plain mappings fail closed;
- duplicate receipt IDs, source remints, future/expired registry/receipt, stale generation, wrong key, altered source/ref/digest, and replay after registry change all hostile-tested;
- preserve existing provider-free/send-free/payment-free/revenue-free authority ceiling;
- compatibility path should make unsafe legacy direct Muse injection impossible, not merely optional to avoid.

Acceptance: update source + all affected existing tests + new hostile tests, normal and `python -O`, demo/runbook, path CI, exact-head review and fresh-main guarded merge/readback. No Slack/email/provider send in this product.

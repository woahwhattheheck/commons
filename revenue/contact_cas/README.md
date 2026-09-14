# Contact CAS — collision-proof first-touch ownership

Two workers can read a coordination feed seconds apart, both see “unclaimed,” and both send. A chat-message claim is not mutual exclusion. **Contact CAS makes the repository blob SHA the lock:** every claim is published with a compare-and-swap update against the exact previously-read `state.json` blob SHA. Of simultaneous writers, at most one succeeds. A failed CAS means **do not send**.

The Python module is deliberately offline. It computes and validates state transitions but never contacts a lead, performs network I/O, or stores credentials.

## Invariant

**No successful remote CAS, no first touch.**

A send has four durable phases:

1. **Claim.** Fetch current `state.json` *and its blob SHA*. Build a `claimed` candidate. Publish it with GitHub `update_file(..., sha=<exact old blob sha>)`. A stale-SHA conflict loses the claim.
2. **Arm.** Hash the exact subject+body, transition the winning claim to `armed`, and publish with another exact-SHA CAS. `armed` does **not** expire automatically.
3. **Gate + send.** Refetch current durable state and require `gate == ALLOW` for the exact target/owner/nonce/message digest. Then perform exactly one provider send.
4. **Receipt.** Hash a non-secret provider receipt/message identifier and CAS-transition `armed` to `sent`. `sent` is terminal for first-touch attempts.

The non-expiring `armed` state closes a second race: if a worker crashes after the provider accepted the message but before the receipt commit, a later worker sees `armed` and stops. Clearing `armed` requires an explicit provider Sent-history check proving the message was not sent.

## Privacy

Raw email addresses are used only locally to derive:

`SHA256("email\\0" + canonical_email)`

Shared state stores only the digest, owner token, nonce, timestamps, exact-message digest, and provider-receipt digest. Never put recipient addresses, message bodies, replies, credentials, or private lead data in `state.json`.

## Local commands

```bash
python contact_cas.py init state.json
python contact_cas.py digest --email 'lead@example.com'
python contact_cas.py message-digest --subject '...' --body-file exact-body.txt
```

Prepare a claim candidate on stdout:

```bash
python contact_cas.py claim state.json \
  --email 'lead@example.com' \
  --owner 'Z-Vector' \
  --nonce 'zv-20260914-0001' \
  --now '2026-09-14T03:50:00Z'
```

Do **not** treat a local file write as ownership. Publish that candidate through a conditional remote update against the exact blob SHA you fetched. Only a successful remote commit owns the lease.

Prepare an armed candidate after drafting the exact message:

```bash
python contact_cas.py arm state.json \
  --email 'lead@example.com' \
  --owner 'Z-Vector' \
  --nonce 'zv-20260914-0001' \
  --now '2026-09-14T03:50:05Z' \
  --message-sha256 '<64 hex>'
```

After that CAS succeeds, refetch current durable state and gate:

```bash
python contact_cas.py gate state.json \
  --email 'lead@example.com' \
  --owner 'Z-Vector' \
  --nonce 'zv-20260914-0001' \
  --message-sha256 '<64 hex>'
```

Only `ALLOW` authorizes that exact first-touch payload.

After provider acceptance, publish a `sent` candidate with the same exact-SHA CAS discipline. `release` works only for an unarmed claim. `reconcile-not-sent --sent-history-checked` is the only automatic recovery path from `armed`, and only after provider Sent history was checked.

## ChatGPT/GitHub connector mapping

For connector workers:

- `fetch_file` the current `state.json` and retain its blob SHA.
- Run this module against those exact bytes to produce a candidate.
- `update_file` **must** receive that exact fetched SHA.
- On conflict/stale SHA, refetch and recompute. Do not send unless a fresh claim later wins.
- After `arm`, refetch and gate from current durable state before sending.
- After send, commit `sent` before releasing custody.

Slack can still carry human-readable coordination, but Slack search freshness is no longer the lock.

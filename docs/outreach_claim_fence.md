# Outreach claim fence v2

`outreach_claim_fence` is a contact-level coordination authority for preventing duplicate outbound contact by concurrent workers. It does **not** send mail/messages, choose recipients, authorize provider/customer/account mutation, move funds, or prove revenue.

## Canonical authority

Production/current authority is code-pinned to one namespace:

- API origin: `https://api.github.com`
- repository: `woahwhattheheck/commons`
- branch: `coordination/outreach-claims-v2`
- root: `.coordination/outreach-claims/v2`
- authority generation: `outreach-claims-v2/2026-09-14`

The CLI exposes no repository/branch/root/API override. Direct API callers that supply a different namespace fail closed. Every stored record and success receipt binds the complete authority identity plus a SHA-256 authority-policy digest.

The default HTTP transport accepts only canonical HTTPS GitHub API URLs and refuses redirects rather than forwarding bearer credentials to a redirect target.

## Safe outbound protocol

The intended order is deliberately asymmetric around the external side effect:

1. `acquire` — atomically reserve the normalized contact.
2. `arm` — bind the exact message digest, channel, and concrete compensation path. This returns a one-time plaintext dispatch token; only its digest is stored.
3. `dispatch` — CAS the exact ARMED generation to `OUTCOME_UNKNOWN` using that token. **Do this before calling the external provider.** A successful dispatch receipt means only that the ambiguity fence is durable; it is not evidence the provider send happened.
4. perform at most one provider send using the already-bound message/channel.
5. on confirmed provider acceptance, `contacted` records digest-only contact evidence and a monotonic re-contact suppression window.
6. if the provider result is missing/ambiguous, do **not** release or reacquire. `OUTCOME_UNKNOWN` blocks reassignment indefinitely, even after ownership time expires.
7. only provider-history evidence signed by a separately controlled reconciliation key can execute `reconcile-unsent` for the exact unknown record generation. That transition proves the coordination layer received a trusted `UNSENT` attestation; it does not itself query a provider.

This closes the crash-after-send gap: time alone never turns an ambiguous external effect into new send authority.

## Lifecycle invariants

- `ACTIVE`: owned reservation, no dispatch commitment.
- `ARMED`: exact message/channel/payment path committed; still insufficient to send.
- `OUTCOME_UNKNOWN`: dispatch capability consumed; blocks reassignment indefinitely until confirmed contact or signed `UNSENT` reconciliation.
- `CONTACTED`: confirmed contact history plus `contact_not_before` suppression.
- `RELEASED`: ownership ended; any existing `contact_not_before` suppression remains authoritative.

`renew` is monotonic and cannot shorten ownership. Contact suppression is stored separately from ownership and cannot be shortened by `renew` or `release`. A stale ARMED reservation may be taken over after ownership expiry because no dispatch capability was consumed; a stale OUTCOME_UNKNOWN reservation may not.

## Privacy and evidence

Raw contact values are used only to derive the deterministic claim key and masked hint. Records store digests, masked hints, ownership, lifecycle state, and paid-path metadata. Message files are hashed through a bounded descriptor read: final symlinks/non-regular inputs are rejected where the platform exposes `O_NOFOLLOW`, size is capped, and descriptor identity/size/timestamps must remain stable across the read.

Compensation paths must contain a concrete paid signal (amount, bounty, paid proposal, contract, invoice, fee, bid/award, etc.). This is an intent/path requirement, not proof of payment.

## CLI

```bash
python -m outreach_claim_fence key --kind email --contact lead@example.com

python -m outreach_claim_fence acquire \
  --kind email --contact lead@example.com \
  --agent-id Z-Tungsten --operation-id OP-123 \
  --opportunity '$1500 paid discovery' --lease-seconds 3600

python -m outreach_claim_fence arm \
  --kind email --contact lead@example.com \
  --agent-id Z-Tungsten --operation-id OP-123 \
  --message-file /path/to/exact-message.txt \
  --channel email --compensation-path '$1500 paid discovery'

# Persist the arm receipt securely and pass its one-time dispatch_token:
python -m outreach_claim_fence dispatch \
  --kind email --contact lead@example.com \
  --agent-id Z-Tungsten --operation-id OP-123 \
  --dispatch-token '<one-time token>'

# Only after the dispatch CAS succeeded may the caller attempt the provider send.
# If provider acceptance is confirmed:
python -m outreach_claim_fence contacted \
  --kind email --contact lead@example.com \
  --agent-id Z-Tungsten --operation-id OP-123 \
  --message-file /path/to/exact-message.txt \
  --channel email --compensation-path '$1500 paid discovery' \
  --cooldown-seconds 259200
```

`GITHUB_TOKEN` is required for remote operations. `reconcile-unsent` additionally requires `OUTREACH_RECONCILIATION_KEY` (minimum 32 bytes) and an exact provider-history digest/signature produced by the trusted reconciliation authority. Ordinary workers should not possess that key.

## Tests

```bash
python -m py_compile outreach_claim_fence/*.py test_outreach_claim_fence.py
python -m unittest -q test_outreach_claim_fence.py
python -O -m unittest -q test_outreach_claim_fence.py
```

The 42-test suite covers canonical namespace pinning, token-origin and redirect fences, authority-bound receipts, normalization, CAS contention, server-time fail-closed behavior, one-time dispatch generation, crash/ambiguity blocking, contact confirmation, CONTACTED release suppression, ACTIVE and CONTACTED renewal monotonicity, contact-history takeover, signed exact-generation UNSENT reconciliation, record/authority tamper, privacy, bounded descriptor file hashing, symlink rejection, and CLI namespace-override rejection.

## Scope ceiling

This is a **contact-level** gate. Organization-wide cross-contact suppression is a separate layer and should compose above this one. A success receipt never grants provider/customer/account mutation authority by itself; the caller must still satisfy the organization-wide lease/history checks and any external-send policy in force.

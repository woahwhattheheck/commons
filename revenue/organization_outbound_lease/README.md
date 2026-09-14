# Atomic Organization Outbound Lease

This package closes one coordination race: two workers can target **different people or routes at the same organization** and therefore both win a per-prospect lock. The organization outbound lease introduces an atomic organization-level writer before any provider send authority is approached.

It composes with, rather than replaces:

1. the organization contact-pressure gate (#14247 / PR #14254), which decides whether more contact pressure is admissible;
2. the per-prospect atomic lock (#14220);
3. opportunity/initial-outreach/provider guards; and
4. the terminal one-shot provider-send consumer (#14049).

## Trust boundary

`acquire` accepts only an HMAC-authenticated pressure attestation whose body is bound to the same organization fingerprint and to exact pressure-receipt, authority-generation and ledger-generation commitments. The host integration must call the landed organization-pressure verifier itself before minting that attestation. The CLI deliberately exposes **no `attest` command**. Acquire also samples process UTC internally: request and pressure-verification timestamps must be current within five minutes, with only five seconds of future skew tolerated, so a once-good pressure receipt cannot be replayed indefinitely.

The organization fingerprint is HMAC-SHA256 over the host's canonical organization identity. Raw organization/contact identity never belongs in lease paths, receipts, branch names or logs. Prospect, route, opportunity and claimant inputs are commitments, not raw labels.

## GitHub atomicity

Production mode uses the GitHub Contents API on a dedicated coordination branch (default `outbound-lease-ledger`):

- acquire creates `active/<org-hmac>.json` **without** a prior SHA; GitHub create-if-absent gives one winner for that path;
- immutable outcome writes create `outcomes/<org-hmac>/<lease-id>.json` without a prior SHA;
- the only releasable terminal is `UNSENT_RELEASED`, and its outcome is committed **before** active deletion;
- release supplies the exact active blob SHA. A stale duplicate releaser cannot delete a successor lease because GitHub rejects a SHA mismatch;
- network/create ambiguity is reconciled by reading the authoritative path. No blind retry is treated as safe.

The coordination branch must already exist and must be restricted to this protocol. The package never creates, force-updates or resets that branch.

## Outcomes

`SENT`, `OUTCOME_UNKNOWN`, `REJECTED`, and `HELD_AUTHORITY` remain blocking. Time passage never frees them. Only an explicit `UNSENT_RELEASED` outcome can remove an active lease and permit a later acquire.

This is intentionally conservative: abandoned/stale leases require owner reconciliation instead of expiry.

## Authority ceiling

A positive result means only **internal organization-lease ownership**. Every receipt hard-codes `externalSendAuthorized=false`. The package has no email/Slack/SMS/form sender and makes no buyer-response, payment, cash, booked-revenue or recognized-revenue claim.

## CLI

```text
python -m revenue.organization_outbound_lease.cli fingerprint --organization-file canonical-org.txt
python -m revenue.organization_outbound_lease.cli acquire --input acquire.json --repository OWNER/REPO
python -m revenue.organization_outbound_lease.cli status --organization-fingerprint HEX --repository OWNER/REPO
python -m revenue.organization_outbound_lease.cli finalize --input outcome.json --repository OWNER/REPO
python -m revenue.organization_outbound_lease.cli release --input unsent-release.json --repository OWNER/REPO
python -m revenue.organization_outbound_lease.cli verify --input lease.json
```

Required secrets are read only from environment variables (`ORG_FINGERPRINT_KEY`, `ORG_PRESSURE_ATTESTATION_KEY`, `ORG_LEASE_NONCE_KEY`, `GITHUB_TOKEN` by default) and are never serialized.

For deterministic local tests, `--store file --store-root DIR` uses a reference create-exclusive store.

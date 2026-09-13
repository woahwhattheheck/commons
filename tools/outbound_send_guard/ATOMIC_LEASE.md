# Atomic outbound send lease

`atomic_lease` closes a concurrency gap that an evidence-only dedupe gate cannot close: two workers can both observe “not sent yet,” both receive clean preflight decisions, and then both cross the provider boundary before either provider receipt is visible.

The lease is deliberately **not** a send-authority engine. A successful lease receipt always says `external_send_authorized=false`. Existing content, owner, cooldown, dedupe, and provider-state gates remain mandatory. This package supplies one missing prerequisite: mutual exclusion for a buyer+offer seam.

## Authority model

The caller supplies stable lowercase machine identities for:

- `buyer_scope` — organization/recipient seam, preferably an organization domain or CRM identity, not a route-specific mailbox;
- `offer_scope` — the exact commercial offer/problem seam;
- `claimant` / `claim_id` / stable `claim_started_at`;
- `preflight_sha256` — digest of the separate outbound preflight evidence;
- `anchor_sha` — an existing commit object in the coordination repository.

The tool hashes only `{schema,buyer_scope,offer_scope}` to form one deterministic Git ref:

`refs/tags/outbound-lease-v1/<sha256>`

Before creating that ref, it creates a non-authoritative annotated Git tag object containing the claim metadata. Ref creation is the atomic event. GitHub allows only one ref at that exact name.

- `201` with the exact tag object means this claim holds the lease.
- `422` (normally “ref exists”) triggers one exact ref readback; another tag object means another claimant won.
- network/408/5xx after the ref POST is outcome-unknown, so the tool performs exactly one ref readback. The lease is recovered only when the ref points to this claim’s exact tag object.
- unreadable, absent, malformed, or differently-owned ref evidence returns HOLD. It never retries the authoritative ref mutation in the same call.

The permanent buyer+offer ref is intentional one-touch state. Route repair must stay with the same durable claim or be explicitly transferred by a higher-level authority; switching from `partners@…` to `info@…` must not create a fresh seam.

## Example claim

```json
{
  "repo":"woahwhattheheck/commons",
  "buyer_scope":"example.com",
  "offer_scope":"lims-migration-validation-pilot",
  "claimant":"Z-Meridian-913506-L91",
  "claim_id":"example-lims-zmer-20260913",
  "claim_started_at":"2026-09-13T09:26:20Z",
  "anchor_sha":"0123456789012345678901234567890123456789",
  "preflight_sha256":"0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
}
```

Run with a GitHub token supplied only through the environment:

```bash
python -m tools.outbound_send_guard.atomic_lease claim.json
```

The CLI never prints the token or Authorization header. Redirects are refused. Network failures become status `0` internally and fail closed at the authority boundary.

## Regression gate

```bash
python -m py_compile tools/outbound_send_guard/atomic_lease.py tools/outbound_send_guard/test_atomic_lease.py
python -m unittest -v tools.outbound_send_guard.test_atomic_lease
python -O -m unittest -v tools.outbound_send_guard.test_atomic_lease
```

Tests cover exact create success, deterministic seam identity, claimant independence, conflicting existing leases, same-claim readback recovery, every indeterminate status, 404/503 readback HOLD, malformed success-body reconciliation, definitive rejection, tag-object failure, strict machine IDs, schema strictness, preflight binding, route/claim metadata separation, content-addressed receipt verification, tamper rejection, ref/seam binding, and the invariant that a lease receipt can never claim external-send authority.

# Trusted Evidence Authority Kernel

A reusable, provider-neutral boundary for one recurring failure class in revenue/readiness rails: **self-consistent evidence is not the same thing as independently trusted current evidence**.

This package makes that distinction executable.

## Guarantees

`verify-current` can emit `CURRENT_SOURCE_AUTHORITY` only when all of these are true:

- the registry file's **raw bytes** match a SHA-256 pinned outside the packet/registry itself;
- every registry source is present exactly once in the packet (no omission-as-success and no undeclared extras);
- source ID, provider, scope, resource, generation, content digest and capture time exactly match the trusted registry;
- source capture is not in the future and has not exceeded its trusted maximum age at **process current UTC**;
- payload bytes are represented by a strict canonical JSON value and match the packet's payload digest;
- registry/packet JSON uses strict duplicate-key parsing, canonical integer semantics and rejects prototype-shaped reserved keys.

`verify-forensic` deliberately cannot emit current authority. Its result is always `HISTORICAL_INTEGRITY`, even when all hashes match. This prevents a caller-selected historical timestamp from backdating stale evidence into a current READY state.

## What this does **not** prove

A SHA-256 does not authenticate AWS, Stripe, Gmail, a procurement portal, a buyer, or any other provider. The trusted registry must be acquired/retained by an integration boundary the candidate packet does not control. In the CLI that trust enters as `--expected-registry-sha256`; deriving that argument from the registry or packet destroys the trust boundary and is forbidden by contract.

The receipt ceiling is source provenance/currentness only. It does **not** authorize provider actions, submissions, purchases, payments, legal/compliance conclusions, batch/clinical release, customer contact, or decision correctness.

## Registry model

Each exact source commitment binds:

- `source_id`
- `provider`
- `scope`
- `resource`
- positive `generation`
- exact `content_sha256`
- exact `captured_at`
- `max_age_seconds`
- `required`

Current verification requires the packet source set to equal the trusted registry source set. A new provider generation, unpublish/reprice, changed account state, changed rules snapshot, or other supersession therefore requires a new independently pinned registry.

## CLI

```bash
python -m revenue.trusted_evidence_authority.cli verify-current packet.json \
  --registry trusted-registry.json \
  --expected-registry-sha256 "$PIN_FROM_INTEGRATION_CONFIG"
```

There is intentionally no `--as-of` on `verify-current`.

Historical replay is explicit and non-authorizing:

```bash
python -m revenue.trusted_evidence_authority.cli verify-forensic packet.json \
  --registry trusted-registry.json \
  --expected-registry-sha256 "$PIN_FROM_INTEGRATION_CONFIG" \
  --as-of 2026-09-13T11:00:00Z
```

## Acceptance

```bash
python -m unittest revenue.trusted_evidence_authority.tests.test_authority -v
python -O -m unittest revenue.trusted_evidence_authority.tests.test_authority -v
python -m revenue.trusted_evidence_authority.acceptance
python -m py_compile revenue/trusted_evidence_authority/*.py revenue/trusted_evidence_authority/tests/*.py
```

The acceptance executable covers valid current evidence plus coordinated self-signing, missing required source, aliasing, superseded generation, stale capture, forensic backdating, duplicate JSON keys, prototype-shaped keys, and payload mutation.

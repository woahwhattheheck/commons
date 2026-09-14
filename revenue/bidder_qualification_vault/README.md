# Bidder Qualification Evidence Vault

A buyer-agnostic, evidence-only authority layer for reusable bidder facts. It lets an opportunity-specific pursuit ask narrow questions such as whether current corporate past-performance, standing, reference-release, staffing, insurance, security, financial-document, signer, or vendor-form evidence is present without copying private source documents into a public proposal carrier.

`EVIDENCE_READY` is deliberately narrow. It means only that the exact query was satisfied by exact host-pinned evidence snapshots for the **independently pinned subject** at evaluation time. It is not bidder qualification, buyer acceptance, reference-contact permission, signature authority, an insurance/security certification, a solvency finding, a bid/submission authorization, an award, payment, or revenue.

## Trust model

Production consumers retain a three-part trust anchor outside caller-controlled query bytes:

1. `expected_subject_id` — the bidder/legal-entity subject this evidence root pair belongs to;
2. `expected_authority_sha256` — the exact authority snapshot root;
3. `expected_registry_sha256` — the exact registry snapshot root.

The public compiler rejects a query whose `subject_id` differs from the independently retained subject. This closes cross-bidder relabeling: changing the query hash is not proof that W-9, standing, insurance, reference, staff, or past-performance evidence belongs to a different company.

Snapshot chronology is also fail-closed. A registry may not predate the authority generation it claims to bind, and no evidence observation inside a registry may postdate that registry's `generated_at`. Equality at the capture boundary is valid.

The shipped v1 evidence engine is preserved byte-for-byte in `_core_v1.py`; `vault.py` is the hardened public facade. `_core_v1.py` is implementation history, not a supported bypass API.

## Evidence classes and semantic boundaries

Supported evidence classes remain `ENTITY_STANDING`, `CORPORATE_PAST_PERFORMANCE`, `CLIENT_REFERENCE`, `STAFF_CREDENTIAL`, `STAFF_AVAILABILITY`, `INSURANCE_ARTIFACT`, `SECURITY_ARTIFACT`, `FINANCIAL_DOCUMENT`, `SIGNER_AUTHORITY`, and `VENDOR_FORM`.

Mechanical boundaries remain unchanged:

- individual prior-employer work cannot satisfy corporate past performance;
- reference release is evidence metadata and never authorizes reference contact;
- financial documents prove presence/period only, never solvency;
- insurance/security artifacts never become adequacy/certification claims;
- staff availability is time-bounded;
- signer evidence never grants signature permission;
- all buyer/contact/submission/signature/pricing/contract/payment/award/revenue authority bits remain false.

## CLI

The CLI is stdin/stdout only and performs no provider, filesystem, customer, payment, or submission mutation.

```bash
python -m revenue.bidder_qualification_vault.vault roots < roots-envelope.json
python -m revenue.bidder_qualification_vault.vault compile < compile-envelope.json > bundle.json
python -m revenue.bidder_qualification_vault.vault verify < verify-envelope.json > verification.json
```

`roots` now requires `authority`, `registry`, and `subject_id`; its output includes `expected_subject_id` beside both roots. This remains setup convenience only: computing roots from supplied bytes is not trust establishment.

`compile` requires `authority`, `registry`, `query`, `expected_subject_id`, `expected_authority_sha256`, and `expected_registry_sha256`. `verify` adds `bundle`. Exit status is `0` current ready, `2` valid current hold, `3` malformed/untrusted/tampered.

Verification still reconstructs the historical bundle byte-for-byte at its recorded evaluation time and then re-evaluates current liveness at the verifier's process-owned UTC time.

## Validation

```bash
python -m py_compile revenue/bidder_qualification_vault/*.py
python -m unittest -v revenue.bidder_qualification_vault.test_vault
python -O -m unittest -v revenue.bidder_qualification_vault.test_vault
```

The test module runs the complete shipped v1 regression suite against the exact byte-preserved core and separately attacks the hardened public facade for trusted-subject transplant, verify-time subject transplant, registry-before-authority chronology, evidence-observation-after-registry chronology, equality boundaries, malformed subject anchors, and CLI trust-anchor enforcement.

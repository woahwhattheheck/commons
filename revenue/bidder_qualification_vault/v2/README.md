# Bidder Qualification Evidence Vault — entity-bound v2

This is the **hardening successor** to the original Bidder Qualification Evidence Vault shipped in Commons issue #14138 / PR #14160 (`85abcb07ac64993fd65f3c0218f6f599198e47c0`), originally owned by **Z-TalonMercury-2123-P6V4**. The v1 implementation remains useful for historical receipt verification; this v2 does not rewrite its source credit.

## Why v2 exists

The v1 trust roots bind an authority ID/generation, registry ID, evidence IDs/classes/source digests, and currentness metadata. Its query also carries `subject_id`, but the trusted authority and registry schemas do **not** carry that subject. Consequently, changing only the query `subject_id` changes the query digest while the same independently retained authority/registry roots can still produce `EVIDENCE_READY`. A trusted company-A evidence set can therefore be relabeled as company-B at query time.

V2 closes that structural gap rather than treating a query label as identity authority:

- the registry root has an explicit `entity_id`;
- every evidence generation has its own `entity_id`;
- a requirement can only consume evidence whose entity matches the registry entity;
- opportunity scope, submission-vs-award stage, verification provenance, revocation/supersession lineage, and exact financial-statement class are explicit;
- same-ID duplicates/drift, lineage forks/cycles, future evidence, and multiple live generations fail closed;
- reference performance, reference permission, and reference contactability are separate authority facts;
- manifests expose only evidence IDs and SHA-256 identities, never private descriptors or document bodies.

### No automatic v1 → v2 subject migration

**Do not copy `v1.query.subject_id` into v2 and call that migration.** V1 did not retain the bidder/entity subject inside its independently retained authority/registry roots, so the missing binding cannot be reconstructed from a query field. A v2 generation requires fresh owner/issuer re-attestation of the entity relationship from the underlying evidence or another independently trusted subject-binding source. Until that re-attestation exists, migration status is `HOLD_PRIVATE_REVIEW` by policy.

## Privacy boundary

V2 may run over private inputs, but its receipt contains only stable evidence IDs and SHA-256 values. It never emits descriptors, issuer text, CV content, tax data, financial-statement content, reference contacts, or other document bodies. Public fixtures are synthetic. **Never commit real W-9s, financial statements, CV PII, reference contact details, tax IDs, credentials, or private proposal evidence.**

## States

Every requirement resolves to exactly one of:

- `CURRENT_VERIFIED`
- `EXPIRED`
- `SUPERSEDED`
- `MISSING`
- `HOLD_PRIVATE_REVIEW`
- `CONFLICT`

A manifest is `ready_for_bid_consumption=true` only when every requested requirement is `CURRENT_VERIFIED`. This is still not proposal/submission authority.

## Key rules

- `SELF_ASSERTED` evidence can never be `VERIFIED`.
- Verified evidence requires a non-`NONE` verifier.
- Same evidence ID appearing more than once is a generation conflict; changed same-ID content cannot be papered over.
- Supersession must name an existing prior generation with the same entity/category/subject. Forks, cycles, self-supersession and cross-entity/category supersession fail closed.
- Future-issued or future-captured evidence is `CONFLICT`.
- `expires_at <= as_of` is `EXPIRED`; a revocation effective at/before `as_of` is `SUPERSEDED`.
- Opportunity-only evidence can satisfy only listed opportunities.
- Submission-stage and award-stage evidence are distinct.
- Financial statements must match the exact required class: `AUDITED`, `REVIEWED`, `COMPILED`, or `OTHER`.
- Reference performance, permission, and contactability are independent categories; a bid that needs all three must request all three.
- Staff CV and staff availability are separate evidence categories.
- Registry and receipt canonicalization are order-independent for evidence/requirements and bind exact SHA-256 content identity.

## CLI

```bash
python -m revenue.bidder_qualification_vault.v2.cli compile input.json --json-out manifest.json --md-out manifest.md
python -m revenue.bidder_qualification_vault.v2.cli verify input.json manifest.json
```

`verify` recompiles from the exact v2 input generation and returns nonzero on any receipt drift.

## Authority ceiling

V2 is offline evidence truth only. It cannot contact a buyer/reference/issuer, sign/certify, set price, accept terms, submit a proposal, mutate a provider/payment account, or assert award/cash/revenue. All receipt authority flags are permanently false.

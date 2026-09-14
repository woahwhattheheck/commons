# Bid Evidence Authority Registry

A buyer-neutral, offline authority layer for reusable company evidence used by proposal and procurement tooling.

It is deliberately **not** an opportunity qualifier, proposal generator, document vault, contact tool, signature service, or submission engine. It answers one narrow question: **does the exact evidence generation requested by a bid remain current, verified, entity-correct, stage-correct, scope-correct and permissioned as of a trusted evaluation time?**

## Why

Live proposals repeatedly need the same owner-controlled facts: entity/registration, W-9, financial-statement class, COI, staff CV/availability, references and reuse permission, certifications, signature authority, and approved commercial inputs. Copying those claims into each pursuit creates stale-generation and invented-evidence risk. This registry gives those pursuits a shared fail-closed manifest without publishing private source documents.

## Privacy boundary

The registry may run over private inputs, but its receipt contains only stable evidence IDs and SHA-256 values. It never emits descriptors, issuer text, CV content, tax data, financial-statement content, reference contacts, or other document bodies. Public fixtures must be synthetic. **Never commit real W-9s, financial statements, CV PII, reference contact details, tax IDs, credentials, or private proposal evidence.**

## States

Every requirement resolves to exactly one of:

- `CURRENT_VERIFIED`
- `EXPIRED`
- `SUPERSEDED` (also used for revoked authority)
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
python -m revenue.bid_evidence_registry.cli compile input.json --json-out manifest.json --md-out manifest.md
python -m revenue.bid_evidence_registry.cli verify input.json manifest.json
```

`verify` recompiles from the exact input generation and returns nonzero on any receipt drift.

## Authority ceiling

The registry is offline evidence truth only. It cannot contact a buyer/reference/issuer, sign/certify, set price, accept terms, submit a proposal, mutate a provider/payment account, or assert award/cash/revenue. All receipt authority flags are permanently false.

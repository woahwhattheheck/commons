# Reference Authority Registry

This is an offline revenue-control surface for keeping **capability evidence** separate from **customer-reference authority**.

A merged open-source fix, internal engineering artifact, paid review-program result, or submitted proposal can be useful capability evidence. None of those facts makes the work a customer engagement or grants permission to name a customer/reference. This registry makes that distinction structural rather than relying on proposal-author memory.

## Boundary

The registry performs no customer or reference contact, permission request, proposal submission, pricing, signature, provider/payment action, accounting, or revenue recognition. It stores no email address, phone number, raw contact identity, credential, or private filesystem path. Source evidence uses public-safe HTTPS references. Authority evidence may instead use a public-safe `opaque:<id>` handle plus SHA-256 commitment so a private permission message or assessment does not need to be published.

`REFERENCE_READY_FOR_OWNER_REVIEW` is **not** authority to disclose or contact. It means only that the supplied evidence currently contains all four independent ingredients for the exact opportunity and exact reference requirement:

1. a real `CLIENT_ENGAGEMENT` evidence record;
2. a current disclosure authority at `PROPOSAL_CAPABILITY` level;
3. a current exact-opportunity/exact-requirement reference permission; and
4. a separate current comparability assessment for that exact requirement.

Capability tags cannot self-declare comparability, and public visibility/payment/merge/receipt/proposal submission cannot self-create reference permission.

## Distinct from opportunity qualification

`revenue/opportunity_qualification/**` decides whether supplied solicitation/capability evidence clears a pursuit route. This package is downstream evidence-reuse custody: **may this specific item be reused in proposal prose, and may this specific real engagement fill this specific named-reference slot?** It does not interpret the buyer packet or decide PRIME/TEAM/NO-BID.

## Input schema

Top-level keys are exact; unknown fields and duplicate JSON keys fail closed.

- `schema_version`: `commons-reference-authority/v1`
- `opportunity`: exact `opportunity_id` and public-safe title
- `requirements[]`: exact opportunity/requirement id, bounded label, `required_count`
- `evidence[]`: immutable evidence id, engagement kind, public-safe subject/performer, source URL/SHA-256, observed result, limitations, disclosure-safe summary
- `disclosure_authorities[]`: exact canonical normalized evidence digest + opportunity + use class + status + observed time/expiry + authority evidence ref/hash
- `reference_permissions[]`: exact canonical normalized evidence digest + opportunity + requirement + status + observed time/expiry + permission evidence ref/hash
- `comparability_authorities[]`: exact canonical normalized evidence digest + opportunity + requirement + COMPARABLE/NOT_COMPARABLE + assessment time/expiry + evidence ref/hash

Supported engagement kinds deliberately separate:

- `CLIENT_ENGAGEMENT`
- `INTERNAL_ENGINEERING`
- `OPEN_SOURCE_CONTRIBUTION`
- `EXTERNAL_REVIEW_PROGRAM`
- `PROCUREMENT_PURSUIT`

Only `CLIENT_ENGAGEMENT` can ever reach reference-ready-for-owner-review. Authority producers should use the exported `evidence_digest()` helper; it hashes the normalized evidence record so harmless input-list ordering cannot change authority identity.

## Time and replay semantics

Production compilation uses process-observed UTC; packet input does not choose current time. The library accepts a timezone-aware `trusted_now` only so tests/controlled callers can reproduce exact semantics.

A receipt binds the normalized, order-independent packet digest and exact evaluation time. `verify_historical()` proves that an old receipt exactly replays at its recorded time. **Historical verification does not refresh authority.** `verify_current()` first verifies the historical receipt, then independently recompiles at fresh trusted current UTC and emits a new current result/receipt. An expired or revoked permission therefore cannot stay current merely because an older receipt was once valid.

## CLI

```text
python revenue/reference_authority/reference_authority.py compile packet.json \
  --json-out review.json --markdown-out review.md

python revenue/reference_authority/reference_authority.py verify packet.json review.json
```

Outputs are canonical JSON plus a human-readable Markdown review. Output authority flags are all false for customer/reference contact, reference disclosure, submission, contract commitment, payment/accounting, and revenue recognition.

The compile command uses create-exclusive output files; it will not overwrite an existing review.

## Fail-closed rules

The implementation rejects duplicate IDs/JSON keys, unknown fields, bool-as-int integers, malformed digests/timestamps/URLs, embedded credentials, email- or phone-shaped contact PII, private/path-shaped public text, unknown evidence/requirement links, unsupported enums, and authority escalation.

Reference promotion also HOLDs on missing permission/comparability/disclosure authority; non-client engagement kind; wrong disclosure class; digest mismatch; future authority; revocation/not-comparable status; expiry; or insufficient exact references for the requirement count.

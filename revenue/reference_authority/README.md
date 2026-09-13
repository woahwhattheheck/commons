# Reference Authority Registry

This offline revenue-control surface keeps **capability evidence** separate from **customer-reference authority**. It is designed so candidate/proposal JSON cannot manufacture the authority that promotes evidence into a named customer reference.

A merged open-source fix, internal engineering artifact, paid review-program result, or procurement pursuit can be useful capability evidence. None of those facts creates a customer engagement, a permission to disclose, or comparability to a buyer requirement.

## Trust boundary

Version 2 has two separate inputs:

1. **Candidate packet** — opportunity, reference requirements, and public-safe evidence only. It contains no engagement-kind field and no disclosure, permission, or comparability authority fields. Unknown fields fail closed.
2. **Host authority registry** — engagement classifications plus disclosure, reference-permission, and comparability records. The entire normalized registry generation is authenticated with HMAC-SHA256 under a host-controlled key loaded only from `COMMONS_REFERENCE_AUTHORITY_HMAC_KEY_HEX`.

The candidate packet cannot supply that key and cannot put a MAC or authority record into its own schema. A self-consistent forged registry with arbitrary opaque handles and 64-hex commitments fails MAC verification before any record can authorize anything. Anyone who possesses the host key is, by definition, operating the trusted authority boundary; key custody is therefore an operational prerequisite and the key must not be committed, placed in candidate packets, Slack, receipts, or proposal artifacts.

This product does not claim that SHA-256 alone proves permission. `authority_sha256`, `permission_sha256`, and `assessment_sha256` are commitments carried **inside the separately authenticated host registry**. They are useful for exact artifact identity after an owner/integration process has verified the underlying evidence; the host registry MAC is what prevents a packet author from inventing the authority generation.

## Reference-ready contract

`REFERENCE_READY_FOR_OWNER_REVIEW` requires all of the following at verifier-observed current time:

- a host-authenticated, current engagement classification for the exact normalized evidence generation;
- that classification says `CLIENT_ENGAGEMENT` and supplies a stable trusted `engagement_id`;
- a host-authenticated current disclosure authority at `PROPOSAL_CAPABILITY` for the exact evidence and exact normalized opportunity generation;
- a host-authenticated current reference permission for that exact evidence, opportunity generation, and requirement generation; and
- a separately host-authenticated current `COMPARABLE` assessment for the same exact generations.

`REFERENCE_READY_FOR_OWNER_REVIEW` is **not** authority to disclose, contact, submit, contract, charge, pay, book revenue, or represent customer approval. Every external-action authority flag in output remains false.

## Distinct reference counting

Buyer `required_count` is counted over unique trusted `engagement_id` values, not evidence IDs. Multiple separately authenticated evidence rows may describe the same underlying engagement; they remain visible in the review but count as one reference. A renamed evidence clone with no host classification is a HOLD and cannot increase the count.

## Generation binding

Authority is bound to normalized generations rather than stable IDs alone:

- engagement classification commits the exact normalized evidence digest;
- disclosure commits exact evidence + normalized opportunity digest;
- permission and comparability commit exact evidence + normalized opportunity digest + normalized requirement digest.

Changing a requirement label or count under the same `requirement_id`, or changing opportunity semantics under the same `opportunity_id`, invalidates older authority with an explicit digest-mismatch HOLD.

The helpers `evidence_digest()`, `opportunity_digest()`, and `requirement_digest()` expose the exact normalization used for those commitments.

## Historical vs current verification

A result receipt binds:

- normalized candidate packet SHA-256;
- exact authenticated authority-registry SHA-256 and generation ID;
- exact evaluation time; and
- the deterministic result body.

`verify_historical(packet, historical_registry, result)` proves replay against the exact historical authenticated generation at the recorded evaluation time.

`verify_current(packet, historical_registry, current_registry, result)` first proves that historical receipt and then performs a fresh reassessment against the supplied **current authenticated registry using the verifier process clock**. The public compile and current-verification APIs accept no clock argument. Deterministic clock injection exists only in underscored test/internal helpers, so a caller cannot backdate the public “current” verifier.

A new registry generation can revoke or supersede old authority while the old generation remains available for historical receipt verification.

## Input schemas

Candidate packet (`commons-reference-authority/v2`):

- `opportunity`: exact id and public-safe title;
- `requirements[]`: exact opportunity/requirement ids, public-safe label, integer `required_count`;
- `evidence[]`: evidence id, public-safe subject/performer, HTTPS source reference + SHA-256, bounded observed result, limitations, and disclosure summary.

Authenticated registry (`commons-reference-authority-trust/v1`):

- fixed host `key_id`, generation id, issuance time, admitted requirement ids;
- `classifications[]`: exact evidence digest → stable engagement id/kind, current/revoked state;
- `disclosures[]`: exact evidence/opportunity generation → disclosure use class/state;
- `permissions[]`: exact evidence/opportunity/requirement generation → permission state;
- `comparabilities[]`: exact evidence/opportunity/requirement generation → comparable/not-comparable state;
- `mac`: HMAC-SHA256 over the canonical normalized registry body.

Authority references may be public-safe HTTPS references or opaque handles. Opaque handles allow the registry to commit to private permission/assessment artifacts without publishing their contents.

## CLI

Set the host verification key in the execution environment, then compile:

```text
COMMONS_REFERENCE_AUTHORITY_HMAC_KEY_HEX=<host-secret-hex> \
python revenue/reference_authority/reference_authority.py compile \
  packet.json authority-registry.json \
  --json-out review.json --markdown-out review.md
```

Historical + fresh-current verification:

```text
COMMONS_REFERENCE_AUTHORITY_HMAC_KEY_HEX=<host-secret-hex> \
python revenue/reference_authority/reference_authority.py verify \
  packet.json historical-authority-registry.json review.json \
  --current-authority-registry current-authority-registry.json
```

If `--current-authority-registry` is omitted, the historical generation is also used for the current reassessment.

Output creation is exclusive. The CLI preflights both output paths, and `_write()` never unlinks a pathname after a post-create failure; this avoids deleting a concurrent replacement that the process did not create.

## Fail-closed behavior

The implementation rejects or HOLDs, as applicable:

- missing/invalid host key or registry MAC;
- authority inserted into candidate JSON;
- caller-selected engagement kind;
- missing/revoked/expired/future/ambiguous classification or authority;
- evidence, opportunity-generation, or requirement-generation digest mismatch;
- renamed aliases without trusted classification;
- duplicate reference evidence for one trusted engagement inflating `required_count`;
- duplicate JSON keys/IDs, unknown fields, bool-as-int integers;
- malformed digests/timestamps/URLs/opaque handles;
- email/phone/path/credential-shaped public data;
- future registry generations;
- substituted historical authority generations;
- result/receipt tampering; and
- any output attempt to elevate external-action authority.

## Scope boundary

No customer/reference contact, permission request, PII store, proposal submission, pricing/signature/contract, provider/payment/accounting mutation, revenue recognition, or customer-approval claim is performed here. The registry is an evidence/review control, not an action system.

This package remains downstream of `revenue/opportunity_qualification/**`: opportunity qualification asks whether a pursuit is supportable; this package asks whether a specific evidence item is authorized for capability reuse and whether a specific trusted client engagement is currently eligible for owner review against a specific reference requirement.

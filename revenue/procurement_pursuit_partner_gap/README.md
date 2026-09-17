# Procurement pursuit gap → partner capability shortlist

Operation: `LIVE-PURSUIT-GAP-TO-PARTNER-SHORTLIST-20260916-ZSOL`  
Issue: `#15142`

This package compiles retained mandatory procurement requirements into four mechanical states:

- `PASS` — an explicitly approved internal crosswalk points to current, supported evidence in an **exact verified generation** of the merged response-module materializer;
- `PRIME_SUPPORTED` — no internal mapping is asserted and an exact current retained prime proof satisfies the required proof kind;
- `PARTNER_REQUIRED` — no internal mapping or current prime proof exists, and the source-bound requirement is explicitly partner-eligible;
- `OWNER_INPUT` — the pursuit source, internal mapping/evidence, or prime proof is stale, missing, ambiguous, pending, unsupported, or otherwise unsafe to promote.

`PARTNER_REQUIRED` rows are deduplicated into an internal capability/proof/workshare shortlist. The shortlist says **what a prime or partner would need to supply**, not which company should be contacted.

## Why this is a separate layer

The package deliberately consumes two already-merged seams instead of copying them:

1. `procurement_response_module_library/materializer.py` owns retained evidence → deterministic response catalog and freshness/proof policy.
2. `partner_workshare_data_room` owns evidence-bound proposed teaming/workshare packets.

This compiler sits between them. It answers “which mandatory pursuit requirements are covered, prime-supported, partner-required, or still owner-input?” and emits capability needs suitable for a later workshare packet.

## Materializer generation is verified, not trusted by filename

A compilation requires the materializer **source, catalog, diff, and receipt** bytes (plus `previous` when that generation used one). The compiler calls `verify_materializer(...)` before using any catalog claim. A copied or tampered catalog cannot create `PASS`.

Even after that verification, internal evidence is rechecked at the pursuit packet’s own `generated_at`. Evidence that was valid when the materializer ran but expired, became stale, or moved outside the module validity window before the pursuit compile becomes `OWNER_INPUT`.

## No semantic matching

There is no fuzzy text match and no model-generated qualification claim.

An internal `PASS` requires:

- `mapping_approval == APPROVED`;
- an explicit `internal_claim_id`;
- the exact claim in the verified generation;
- the materializer record to remain `SUPPORTED`;
- the catalog module to remain `APPROVED`;
- exact family and claim-kind agreement;
- requirement applicability tags to be a subset of the retained evidence tags;
- all linked evidence to remain supported and current at compile time.

`PENDING` mappings never fall through to a partner route; they become `OWNER_INPUT`.

## Prime proof rules

Prime evidence is source-bound, exact-requirement evidence with `VERIFIED` or `PROVISIONAL` status and an explicit expiry. A `PRIME_SUPPORTED` result requires every supplied proof for that requirement to be current and `VERIFIED`, with an exact proof-kind match.

Proof kinds are mechanical:

| Claim kind | Required proof kind |
| --- | --- |
| `CAPABILITY` | `CAPABILITY_PROOF` |
| `POLICY` | `POLICY_PROOF` |
| `CERTIFICATION` | `ISSUER_VERIFIED_CERTIFICATION` |
| `REFERENCE` | `REFERENCE_PERMISSION_RECEIPT` |
| `SLA` | `ACCEPTED_SLA_RECEIPT` |
| `SECURITY_CONTROL` | `CONTROL_TEST_RECEIPT` |

This prevents a generic capability artifact from satisfying a certification, reference, SLA, or security-control requirement.

## Pursuit source currentness

Each pursuit carries a credential-free HTTPS source URI, SHA-256, observed time, expiry, and caller-retained authority label. The compiler checks age/future/expiry mechanically.

The label is **not provider-authenticated**. `buyer_officialness_authenticated` remains false even when the caller retained `BUYER_OFFICIAL`. A current five-or-more-item retained set may reach `RETAINED_CURRENT_CARRIER_SET_READY_FOR_OWNER_REVIEW`; that still means retained input ready for human review, not proof that the buyer published it.

`SYNTHETIC_FIXTURE` sources never become live evidence and classify to `OWNER_INPUT`.

## Live materialization status

`LIVE_MATERIALIZATION_STATUS.json` records the build-time finding at the claim commit: no trustworthy 5–10-item retained-current carrier set with source URI/SHA/currentness was proven for this build. Therefore the durable live status is:

`LIVE_MATERIALIZATION_BLOCKED_NO_VERIFIED_CARRIER_SET`

The compiler and tests still ship so a real carrier set can be attached later without redesigning the truth boundary.

## Synthetic exercise

First compile the adjacent synthetic materializer source with the merged materializer:

```bash
python -m revenue.procurement_response_module_library.materializer \
  compile \
  --source revenue/procurement_pursuit_partner_gap/synthetic_materializer_source.json \
  --out-dir /tmp/materializer-generation
```

Then compile the multi-pursuit fixture:

```bash
python -m revenue.procurement_pursuit_partner_gap.compiler \
  compile \
  --request revenue/procurement_pursuit_partner_gap/synthetic_pursuits.json \
  --materializer-source revenue/procurement_pursuit_partner_gap/synthetic_materializer_source.json \
  --materializer-catalog /tmp/materializer-generation/catalog.json \
  --materializer-diff /tmp/materializer-generation/diff.json \
  --materializer-receipt /tmp/materializer-generation/receipt.json \
  --out-dir /tmp/pursuit-gap-generation
```

The output directory is create-only and contains `gap_packet.json` and `gap_receipt.json`.

Verify:

```bash
python -m revenue.procurement_pursuit_partner_gap.compiler \
  verify \
  --request revenue/procurement_pursuit_partner_gap/synthetic_pursuits.json \
  --materializer-source revenue/procurement_pursuit_partner_gap/synthetic_materializer_source.json \
  --materializer-catalog /tmp/materializer-generation/catalog.json \
  --materializer-diff /tmp/materializer-generation/diff.json \
  --materializer-receipt /tmp/materializer-generation/receipt.json \
  --packet /tmp/pursuit-gap-generation/gap_packet.json \
  --receipt /tmp/pursuit-gap-generation/gap_receipt.json
```

## Authority ceiling

This package does not authenticate buyer or provider identity, certify qualifications, recommend a partner, authorize partner/buyer contact, authorize email/outreach, authorize a bid/submission/signature, commit price, recognize an award, authorize invoice/payment, or recognize revenue. Every packet and receipt records those authorities as false.

Any later external route must be independently coordinated and, in this workspace, pass Muse single-writer arbitration before send.

## Tests / CI

`test_compiler.py` covers exact internal PASS, pending/missing/stale internal evidence, pursuit-source currentness, materializer-generation tamper, sensitive proof kinds, prime proof expiry/provisional state, partner deduplication, carrier-set state, strict JSON/hash/URI rules, receipt/output tamper, and authority ceilings.

The workflow is path-scoped, one job, normal + optimized Python, concurrency-cancelled, and does not add a runner matrix.

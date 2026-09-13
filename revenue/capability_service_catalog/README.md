# Capability-backed service catalog compiler

`revenue/OFFERING_FAMILIES.md` defines **Services** as a first-class Commons revenue family and says the next expansion is to route every demonstrated capability into at least one bounded service deliverable. This package turns explicit, immutable capability evidence plus exact owner-approved service mappings into deterministic **human-review evidence** for that catalog work.

It is deliberately not a sales bot. `READY_FOR_HUMAN_SERVICE_CATALOG_REVIEW` never means published, offered, sold, contracted, fulfilled, accepted, paid, or recognized as revenue.

## What is bound

Each demonstrated capability must cite an immutable `owner/repo` + 40-hex commit + normalized path + SHA-256, plus a dated outcome/verification receipt. Each service mapping binds:

- one or more demonstrated capability IDs;
- an allowed service mode and concrete delivery format;
- at least one deliverable, and at least one acceptance criterion per deliverable;
- explicit exclusions and dependencies;
- either owner-approved exact integer minor-unit fixed pricing or explicit unpriced scope review;
- an owner-approval reference whose `mapping_sha256` exactly commits to the validated, normalized complete service mapping and whose validity window includes the trusted `as_of` instant. Call `mapping_sha256(mapping)` before owner approval so incidental list ordering cannot change approval identity.

Every demonstrated capability must be covered by at least one service. Evidence from the future or older than the configured trusted-age limit holds the whole package. Service approval may not predate the evidence it relies on.

## Fail-closed boundaries

The compiler rejects duplicate JSON keys, non-finite numbers, unknown object keys, mutable/non-40-hex source refs, malformed digests, duplicate IDs, unsupported service modes/formats, duplicate capability references, deliverables without acceptance criteria, boolean/float/negative fixed-price values, approval digest drift, secret-shaped strings, email-shaped PII, SSN-shaped PII, and malformed UTC timestamps.

Semantic HOLDs include stale/future evidence, unknown capability references, mode mismatches, uncovered demonstrated capabilities, owner approval from the future, expired approval, approval predating evidence, and approval-to-mapping digest mismatch.

## Deterministic outputs

`compile_catalog()` produces a canonical package containing a catalog and content-addressed receipt. `verify_package()` independently recomputes the complete package from the input and trusted clock. `render_csv()` and `render_markdown()` are deterministic projections of that verified package.

The CLI writes only into a newly created output directory and uses create-exclusive file publication. Existing files are never clobbered.

```bash
python -m revenue.capability_service_catalog.cli input.json \
  --as-of 2026-09-13T10:00:00Z \
  --max-evidence-age-days 90 \
  --out-dir service-catalog-out
```

Exit `0` means review-ready evidence; exit `3` means HOLD. A parse/schema/integrity error is a hard failure.

## Authority

All emitted authority flags remain false for catalog publication, buyer contact, offer/send, contract execution, fulfillment, checkout/payment, buyer acceptance, and cash/revenue. Synthetic fixtures are tests only.

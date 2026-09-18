# Massachusetts DDS IPMS RFI market-response compiler

This package implements the internal evidence-bound carrier for Massachusetts EOHHS/DDS solicitation `BD-27-1039-EHS01-ASHWA-133015` / `27EHSPMDDSIPMSRFI`.

It is intentionally fail-closed about buyer bytes and vendor facts. The compiler does **not** send a response, mutate COMMBUYS, claim TJLabs owns a production IPMS, invent legal/company/certification facts, invent prices, sign, spend, or claim an award/payment/revenue result.

## What it enforces

- strict source/amendment ledger with controlling vs. secondary authority, freshness, supersession and SHA-256 fields;
- immutable capability IDs and states `SUPPORTED | CONFIGURABLE | THIRD_PARTY | PLANNED | NOT_SUPPORTED | UNKNOWN`, with affirmative states evidence-bound to the exact capability subject;
- required responsible-AI/privacy facts, all evidence-bound when known;
- architecture and compatibility facts with explicit unknown/owner-input states;
- five-year TCO components separated by category, with owner/vendor-only input provenance and exact integer-cent arithmetic;
- deterministic question-to-answer response pack, canonical JSON, Markdown and tamper receipt;
- readiness limited to `RESEARCH_READY`, `RESPONSE_DRAFT_READY`, or `HOLD`;
- hostile validation for duplicate IDs/JSON keys, bool-int aliasing, unknown fields, malformed hashes/times, future/stale evidence, evidence transplant, source downgrade, unsupported affirmative capability claims, facial-recognition contradictions, missing privacy facts, TCO mismatch and receipt tamper.

## Current buyer header

The public COMMBUYS header was re-observed on 2026-09-15 and identifies the solicitation as OPEN, electronic-quote enabled, with an opening deadline of 2026-10-01 15:00 ET. It lists two buyer attachments: the RFI and its response template. Those attachment **bytes are not embedded here**; `example_input.json` therefore keeps both SHA-256 values unavailable and readiness at `HOLD`.

Controlling notice: <https://www.commbuys.com/bso/external/bidDetail.sda?docId=BD-27-1039-EHS01-ASHWA-133015&external=true&parentUrl=close>

## CLI

```bash
python -m opportunities.mass_dds_ipms_rfi.compiler compile \
  opportunities/mass_dds_ipms_rfi/example_input.json \
  --json-out /tmp/mass-dds-response.json \
  --md-out /tmp/mass-dds-response.md \
  --receipt-out /tmp/mass-dds-receipt.json

python -m opportunities.mass_dds_ipms_rfi.compiler verify \
  opportunities/mass_dds_ipms_rfi/example_input.json \
  /tmp/mass-dds-response.json \
  /tmp/mass-dds-receipt.json
```

The checked-in example is deliberately incomplete and should compile to `HOLD`. To reach `RESPONSE_DRAFT_READY`, a future operator must provide current controlling buyer-document bytes/hashes, company/contact/product identity, evidence for every material affirmative capability/privacy/architecture/compatibility claim, five-year TCO inputs, and all required response fields. That still does not authorize submission.

## Future RFR/RFQ reuse

The response JSON exposes source IDs, capability states, privacy values, five-year TCO totals and blockers in stable machine-readable form. When a later RFR/RFQ appears, carry forward only evidence whose source/currentness still validates; do not infer production behavior from this RFI research packet.

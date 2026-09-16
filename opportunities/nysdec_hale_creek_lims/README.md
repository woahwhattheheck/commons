# NYS DEC Hale Creek Field Station LIMS RFI — CR#2138876

This directory is an internal, source-bound response/readiness carrier for Commons issue **#14864**.

## Current disposition

`DIRECT_COTS_LIMS_PRIME=HOLD`

`TEAMING_ROUTE_OPEN_INTERNAL`

The controlling buyer notice describes an **RFI / market-research** exercise. It is not an RFP, IFB, RFQ, award, contract, or procurement commitment. The retained timetable records a September 29 vendor-question date and October 20 RFI-response date, but the compiler deliberately marks deadline currentness non-authoritative: any external action requires a fresh official-source check.

## What the carrier does

`source_snapshot.json` retains the published opportunity identity, current environment, objectives, Desired Requirements 1–14, Information Requested 15–28, response format, and general terms. `carrier.py` binds the exact source bytes by SHA-256 and emits a deterministic 28-question response scaffold.

The status taxonomy is intentionally narrow:

- `PARTNER_REQUIRED`: a qualified commercial LIMS prime must supply the authoritative product/platform/support response.
- `EVIDENCE_REQUIRED`: TJLabs has no retained current evidence for an affirmative commercial/compliance/customer/staffing/contract-vehicle claim.
- `SUPPORTED_INTERNAL`: only question 27's desired-partner/workshare description is supported internally.
- `NOT_CLAIMED`: reserved for future source generations; not used to silently convert a missing answer into a positive one.

The compiler has **no caller-supplied qualification form**. Question statuses, partner boundaries, non-binding RFI truth, ROM status, and external-authority flags are code-owned. Verification recomputes the complete receipt and rejects any changed answer, status, authority flag, date, evidence claim, or price.

## AquaTrace evidence boundary

The carrier cites merged `woahwhattheheck/aquatrace-lims#159` / merge `3aa038bf56117465a92e4026dda4498932085922` only as internal engineering-pattern evidence for migration reconciliation, stable identities, replay/idempotency, discrepancy detection, audit/correction receipts, quality holds, schema-bound export candidates, and cutover/UAT evidence.

That artifact does **not** prove a commercial COTS LIMS product, production customer deployments, NYS/DEC security compliance, hybrid production hosting, 24×7×365 support, warranties, equipment replacement, OGS/GSA vehicle access, staffing/clearances, references, or buyer acceptance.

## Commercial boundary

The RFI asks for rough-order cost information, but cost figures are explicitly non-binding. This carrier returns `NOT_PRICED` because platform licensing, production hosting, support/warranty, deployment, and partner responsibilities are not retained. It does not recycle the Stockton workshare price or invent buyer pricing.

Potential paid TJLabs scope under a qualified LIMS prime is limited to:

- legacy-data migration reconciliation and rollback evidence;
- instrument/data-interface replay and idempotency verification;
- source-to-target discrepancy and duplicate detection;
- schema-bound import/export acceptance verification;
- quality-hold, audit, correction, and provenance receipts;
- cutover/UAT acceptance evidence.

No partner is selected or represented by this carrier.

## Commands

```bash
python opportunities/nysdec_hale_creek_lims/carrier.py compile \
  --source opportunities/nysdec_hale_creek_lims/source_snapshot.json \
  --output /tmp/hale-creek-receipt.json

python opportunities/nysdec_hale_creek_lims/carrier.py verify \
  --source opportunities/nysdec_hale_creek_lims/source_snapshot.json \
  --receipt /tmp/hale-creek-receipt.json

python -m unittest -v tests.test_nysdec_hale_creek_lims
python -O -m unittest -v tests.test_nysdec_hale_creek_lims
```

## Authority ceiling

The emitted receipt permanently keeps these false: external contact, RFI submission, partner representation, contract acceptance, award, payment, and revenue authority. External buyer or partner contact is separately single-writer gated by fresh official-source recensus, Slack/Gmail/GitHub dedupe, and Muse arbitration.

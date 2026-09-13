# OHSU Digital Pathology IMS — qualification and synthetic integration evidence

Evidence-only internal tooling for **OHSU RFP-2027-2012, Digital Pathology Image Management System**.

## Why this exists

OHSU's public procurement page lists the opportunity as issued **2026-09-11** and due **2026-10-11**. The public description requires an enterprise digital-pathology IMS with bi-directional Epic Beaker integration, end-to-end clinical pathology workflows, centralized image management/view/share/analyze capability, and scalable native/third-party AI and image-analysis integration across clinical, educational, and research missions.

Critically, OHSU's listing also tells respondents to read and confirm **minimum requirements contained in the RFP document**. The public summary therefore is not enough to establish bidder eligibility.

This pack turns that boundary into code:

- `qualification.py` binds the exact opportunity identity and public source, requires a captured full-RFP digest before eligibility can become READY, requires explicit minimum-qualification rows, and requires evidence for every mandatory row.
- A public-listing-only capture deterministically returns `HOLD`; it can never silently become bidder qualification.
- Receipts are content-addressed and explicitly deny outreach, intent-to-bid, proposal submission, clinical use, payment, and buyer-acceptance authority.
- `integration_contract.py` provides a PHI-free synthetic bidirectional Beaker↔IMS trace model. It tests correlation, exact replay collapse, message-id conflict rejection, and provenance without claiming Epic certification or clinical interoperability.

## Truth / authority boundary

`READY_FOR_INTERNAL_BID_REVIEW` means only that a locally captured minimum-qualification snapshot has evidence for every mandatory row. It does **not** mean OHSU has accepted the bidder, that Epic has certified an integration, that an IMS is clinically validated, or that anyone may contact OHSU / submit an intent / submit a proposal.

The synthetic integration fixture contains no patient information and is not connected to Epic, Beaker, an IMS, OHSU, or any clinical system.

## Validation

```bash
cd revenue/ohsu_digital_pathology_ims
python -m py_compile qualification.py integration_contract.py cli.py test_qualification.py test_integration_contract.py test_cli.py
python -m unittest -v
python cli.py fixtures/public_listing_only.json --evaluated-at 2026-09-13T09:30:00Z
python -O -m unittest -v
```

Expected focused suite: 32 tests.

The CLI uses exit `0` only for `READY_FOR_INTERNAL_BID_REVIEW`, `3` for a truthful `HOLD`, and `2` for malformed/unreadable evidence. Receipts can be written atomically with `--output`.

## Next evidence step

Acquire the official RFP package through the procurement process, hash the exact source package, transcribe the actual minimum qualifications into `minimum_qualifications`, attach content-addressed evidence references, then rerun the gate. Until then, `HOLD` is the correct result.

No external outreach or submission is performed by this module.

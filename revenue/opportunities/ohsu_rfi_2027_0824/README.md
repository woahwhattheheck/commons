# OHSU RFI-2027-0824 — response-evidence carrier

Internal, deterministic evidence tooling for OHSU's **Artificial Intelligence-Enabled Accounts Payable Automation Solution** RFI.

The carrier does two things:

1. makes unsupported response claims mechanically visible (`PARTNER_REQUIRED`, `OWNER_REQUIRED`, `HOLD`) instead of letting proposal prose imply Oracle EBS R12 experience or customer outcomes we cannot prove;
2. supplies a synthetic AP acceptance harness plus a shipped 24-case acceptance matrix for PO presence, vendor match, tolerance, duplicates, approvals, reconciliation, deterministic exception states, and content-addressed receipts.

It intentionally does **not** write Oracle, pay suppliers, contact OHSU, contact a partner, submit an RFI, accept terms, or claim customer results. The included $2,500 / 3-business-day specialist package is `PROPOSED_NOT_ACCEPTED` only.

## Official source facts bound by the fixture

- Buyer: Oregon Health & Science University.
- RFI: `RFI-2027-0824`.
- Topic: AI-enabled AP automation integrated with on-premises Oracle E-Business Suite R12.
- Areas: invoice intake/validation, matching, coding, approvals, Oracle transaction processing, inquiries, statement reconciliation, exception management, reporting, audit controls; plus implementation requirements, comparable customer experience, expected automation outcomes, and indicative pricing.
- Intent deadline: not applicable.
- Response due: September 23, 2026, 5:00 PM Pacific (`2026-09-24T00:00:00Z`).
- Official listing: `https://www.ohsu.edu/procurement/bids`.

The manifest binds a SHA-256 over the normalized controlling OHSU facts, and VERIFIED local-test evidence is accepted only when its digest matches the exact shipped harness/test/matrix bytes. The source digest is a normalized-facts digest, not a claim to hash OHSU's entire HTML page.

## Run

```bash
python -m unittest -v test_ohsu_carrier.py
python -O -m unittest -v test_ohsu_carrier.py
python run_acceptance_matrix.py fixtures/ap_cases.json --json-out /tmp/ohsu-ap-matrix.json
python build_packet.py fixtures/manifest.json \
  --as-of 2026-09-14T04:00:00Z \
  --json-out /tmp/ohsu-packet.json \
  --md-out /tmp/ohsu-packet.md
```

## Commercial posture

Direct response is HOLD while demonstrated Oracle EBS R12 transaction-processing and comparable-customer proof are absent. Teaming is the truthful route: a qualified Oracle prime owns its credentials and architecture; this lane offers a bounded response-evidence/acceptance pack with deterministic fixtures and unsupported-claim controls.

# RCAP DCS / technology ecosystem assessment direct-bid carrier

Operation: `RCAP-DCS-ASSESSMENT-DIRECT-BID-ZNP-20260917`

This subtree carries the **$24,500 fixed / PROPOSED_NOT_ACCEPTED** direct proposal for RCAP's **CRM System Assessment and Strategic Planning Services** procurement while failing closed on external submission authority.

## Frozen commercial state

- Base offer: **$24,500 fixed / PROPOSED_NOT_ACCEPTED**.
- Six 60-minute virtual stakeholder discovery sessions plus kickoff and a 60-minute findings presentation.
- Estimated four-week delivery from kickoff and mutually agreed access/materials.
- Optional **$7,500 fixed** implementation-procurement readiness package is **excluded from the base fee and not accepted**.
- No travel is planned or included; no direct expenses are anticipated.

## Exact submission route

The first-party submission route is `gtodd@rcap.org` for Griffin Todd, Data & IT Manager, recovered from RCAP's current first-party RFP page:
`https://www.rcap.org/careers/rfp-assessment-strategic-planning-services/`

Route resolution is evidence, **not send authority**. Repository state cannot authorize buyer contact or submission. Any eventual external submission still requires the current Muse/single-writer boundary, an immediate Slack + Gmail recensus, and exactly one provider send. Provider-SENT must become hard DNR before any other seat acts.

No buyer contact, submission, receipt, shortlist/interview, selection, executed SOW, insurance sufficiency, acceptance, award, payment, receivable, or revenue is represented here.

## Submission packet

Current internal PDF candidate:
- `Token_Junkie_Labs_RCAP_DCS_Assessment_Proposal_2026-09-17.pdf`
- SHA-256 `86a389a0314f1d4f30f3378f4ec491f7f7955a4a77cee378f7f72682ff5f422f`
- 5 pages
- rendered and visually inspected across all five pages
- no public Commons repository/Pages/raw/API/codeload/SSH backlink in the buyer-facing source
- exact proposal source SHA-256 `81577b649507ea45e4733c30dbe2bdc1c8b234a5d96761a3c9573345d8a65b12`

The validator hashes the committed PDF bytes directly before declaring `submission_artifact_ready=true`.

The superseded six-page pre-policy artifact remains provenance only:
- SHA-256 `5ac9ec259979476fdfac66929f51ba9febc8c87a36e2fe069231646ac4bfc2c6`
- reason `PRE_POLICY_PDF_CONTAINS_FORBIDDEN_COMMONS_BACKLINK`
- it must never be used for submission.

## Validation

From this directory:

    python validate_recovery.py
    python -m unittest discover -s tests -v
    python -O -m unittest discover -s tests -v
    python -m py_compile validate_recovery.py tests/test_rcap_recovery.py

A valid packet means only: route resolved; sanitized PDF bytes match the inspected hash; source has no public Commons backlink; and buyer contact/submission/acceptance/payment/revenue authority remain false.

# RCAP DCS / technology ecosystem assessment direct-bid carrier

Operation: `RCAP-DCS-ASSESSMENT-DIRECT-BID-ZNP-20260917`

This subtree freezes the existing **$24,500 fixed / PROPOSED_NOT_ACCEPTED** direct proposal for RCAP's **CRM System Assessment and Strategic Planning Services** procurement while failing closed on external submission authority.

## Frozen commercial state

- Base offer: **$24,500 fixed / PROPOSED_NOT_ACCEPTED**.
- Six 60-minute virtual stakeholder discovery sessions plus kickoff and a 60-minute findings presentation.
- Estimated four-week delivery from kickoff and mutually agreed access/materials.
- Optional **$7,500 fixed** implementation-procurement readiness package is **excluded from the base fee and not accepted**.
- No travel is planned or included; no direct expenses are anticipated.

The proposal is vendor-neutral. It does not include implementation, production changes, penetration testing, legal/compliance opinions, migration execution, licensing, or vendor selection.

## Submission route

The exact first-party submission route is now resolved as `gtodd@rcap.org` for Griffin Todd, Data & IT Manager. The route was independently recovered on 2026-09-17 from RCAP's current first-party RFP page:

`https://www.rcap.org/careers/rfp-assessment-strategic-planning-services/`

Route resolution is evidence, **not send authority**. Repository state cannot authorize buyer contact or submission. Any eventual external submission still requires the current single-writer/Muse boundary, an immediate Slack+Gmail recensus, a submission-eligible regenerated PDF, and exactly one provider send. Provider-SENT must become hard DNR before any other seat acts.

No buyer contact, submission, receipt, shortlist/interview, selection, executed SOW, insurance sufficiency, acceptance, award, payment, receivable, or revenue is represented here.

## Public-surface recovery

The original proposal source named the internal Commons repository as a public work sample. That is no longer allowed on buyer/customer-facing artifacts. The current proposal source removes that backlink and does not invent a replacement reference or work sample.

The previously rendered PDF is retained only as historical evidence. **Do not submit it.** It was rendered from the pre-policy source generation and is therefore marked `submission_eligible=false` / `regeneration_required=true`. A new PDF must be regenerated from the sanitized source and independently verified before any send lane can proceed.

## Proposal artifacts

- Historical PDF — **NOT SUBMISSION ELIGIBLE**
  - filename `Token_Junkie_Labs_RCAP_DCS_Assessment_Proposal_2026-09-17.pdf`
  - SHA-256 `5ac9ec259979476fdfac66929f51ba9febc8c87a36e2fe069231646ac4bfc2c6`
  - 6 pages
  - prior visual verification remains historical evidence only
- `PROPOSAL_SOURCE_20260917.md` — current sanitized human-readable proposal source.
- Historical DOCX SHA-256 `28c201eb78cf12f2db7abdba23f406ed47b3f64183aeb2f0214b79c07760c60a`; the DOCX itself is not published in this subtree.

## Validation

From this directory:

    python validate_recovery.py
    python -m unittest discover -s tests -v
    python -O -m unittest discover -s tests -v

A valid current packet means: exact RCAP route resolved from first-party evidence; source has no public Commons backlink; old PDF is ineligible and regeneration is required; buyer contact/submission/acceptance/payment/revenue authority remain false.

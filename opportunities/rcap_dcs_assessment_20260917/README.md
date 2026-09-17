# RCAP DCS / technology ecosystem assessment direct-bid carrier

Operation: `RCAP-DCS-ASSESSMENT-DIRECT-BID-ZNP-20260917`

This subtree freezes a complete, visually verified direct proposal for RCAP's **CRM System Assessment and Strategic Planning Services** procurement while failing closed on external submission authority.

## Frozen commercial state

- Base offer: **$24,500 fixed / PROPOSED_NOT_ACCEPTED**.
- Six 60-minute virtual stakeholder discovery sessions plus kickoff and a 60-minute findings presentation.
- Estimated four-week delivery from kickoff and mutually agreed access/materials.
- Optional **$7,500 fixed** implementation-procurement readiness package is **excluded from the base fee and not accepted**.
- No travel is planned or included; no direct expenses are anticipated.

The proposal is vendor-neutral. It does not include implementation, production changes, penetration testing, legal/compliance opinions, migration execution, licensing, or vendor selection.

## Submission boundary

RCAP's first-party RFP names Griffin Todd, Data & IT Manager, as the email recipient, but the public page available to this carrier masks the exact mailbox. The exact route is deliberately `null`: **do not guess it**.

Repository state cannot authorize buyer contact or send. External submission requires an independently resolved exact route, a Muse single-writer election for the exact buyer × route × RFP × purpose, an immediate Slack+Gmail recensus, and exactly one frozen-PDF send. Provider-SENT must become hard DNR before any other seat acts.

No buyer contact, submission, receipt, shortlist/interview, selection, executed SOW, insurance sufficiency, acceptance, award, payment, receivable, or revenue is represented here.

## Proposal artifacts

- Frozen submission PDF (generated and visually verified in the originating session; binary not committed by this connector)
  - filename `Token_Junkie_Labs_RCAP_DCS_Assessment_Proposal_2026-09-17.pdf`
  - SHA-256 `5ac9ec259979476fdfac66929f51ba9febc8c87a36e2fe069231646ac4bfc2c6`
  - 6 pages
  - visually verified after independent PDF rendering
- `PROPOSAL_SOURCE_20260917.md` — frozen human-readable proposal source matching the visually verified submission artifact.
- Final local DOCX SHA-256 `28c201eb78cf12f2db7abdba23f406ed47b3f64183aeb2f0214b79c07760c60a`; the DOCX itself is not published in this subtree.

## Validation

From this directory:

```bash
python validate_recovery.py
python -m unittest discover -s tests -v
python -O -m unittest discover -s tests -v
```

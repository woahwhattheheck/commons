# WRF 5417 — Camera-Based AI Monitoring Proposal Carrier

**Operation:** `WRF-5417-CAMERA-AI-PROPOSAL-ZCHK4N7-20260913`  
**Owner:** `Z-CassiniHarbor-913841-K4N7` (`ZCH-K4N7`)  
**Internal status:** `HOLD — technically packageable, not yet submission-ready`

## Why this carrier exists

On 2026-09-13 WRF Research Manager George Kajjumba replied to the existing outreach and explicitly directed Token Junkie Labs to WRF's open competitive RFP process for Project 5417. While the solicitation is open, no off-process project-services pitch should be sent.

The public opportunity is **WRF RFP 5417 — Developing Camera-Based AI Algorithms to Monitor Water Quality at Water and Wastewater Utilities**. Proposals are due **2026-09-14 at 3:00 PM Mountain Time**, WRF funding is capped at **$300,000**, the expected project period is **24–30 months**, and the applicant must supply eligible contribution of at least **33% of the WRF award requested**.

This directory is intentionally fail-closed. It contains a source-bound response architecture and a deterministic readiness check, but it does **not** claim Token Junkie Labs currently has the organizational portal account, financial packet, signed forms, PI/Co-PI disclosures, cost-share commitments, utility participation, or domain qualifications needed for a valid submission.

## Controlling public sources

- Opportunity / grant record: https://portal.waterrf.org/outbound-grant-details/3352
- RFP PDF: https://portal.waterrf.org/core/media/media.nl?_xt=.pdf&c=9336228&h=cCxr5g0fgMTJUDdMOEXrnmb7aH-IpjJ_XeWHQ52sRsNxGB44&id=365738
- 2026 Research Priority Program Guidelines: https://portal.waterrf.org/core/media/media.nl?_xt=.pdf&c=9336228&h=8Plt54arIryvX-1alddYXDGtMziqlp1t7ThZLFBn_LZmAcXE&id=350043

The portal currently renders the deadline as `09/14/2026 3:00 pm ... Mountain Time` and also exposes a GMT-07 label. The RFP itself says 3:00 PM Mountain Time. The validator uses the IANA zone `America/Denver` for a conservative clock computation and keeps `deadline_offset_recheck` as a hard human verification gate. The final submitter must verify the live portal clock before relying on the computed UTC instant.

## Current decision

**Direct-prime: HOLD.** For-profit entities are eligible in principle, but eligibility is not the same thing as submission readiness. Current evidence has not established:

- a WRF organizational My Portal account for the applying entity;
- signed W-9 / entity-specific tax documentation as applicable;
- required financial statements and grant-management capability materials;
- signed Certification and Assurance materials;
- named PI / Co-PIs and Current & Pending forms;
- a consenting multi-site utility field-demonstration team;
- evidence-backed computer-vision + water/wastewater research qualifications;
- exact applicant / third-party contribution commitments meeting the minimum;
- a completed WRF budget workbook and narrative;
- owner-authorized legal/IP/financial review and final portal submission.

The correct route is therefore **build the submission package while holding final submission authority**. If the hard gates become evidenced before the deadline, this carrier can be promoted. Otherwise it remains a reusable teaming/partner packet rather than a fabricated prime response.

## Package

- `requirements.json` — source-bound mandatory and scored requirements.
- `proposal_draft.md` — internal technical/management/communications response architecture. Bracketed fields are deliberately unresolved.
- `submission_manifest.json` — default fail-closed readiness ledger.
- `validate_readiness.py` — deterministic readiness validator.
- `tests/test_validate_readiness.py` — hostile regressions for deadline, cost share, utility consent, evidence and READY spoofing.

Run:

```bash
python opportunities/wrf_5417_camera_ai/validate_readiness.py \
  opportunities/wrf_5417_camera_ai/submission_manifest.json

python -m unittest opportunities.wrf_5417_camera_ai.tests.test_validate_readiness
```

A default run **must return HOLD / non-zero**. That is expected and protective.

## Authority boundary

This carrier may research public sources, draft internal response material, compute non-binding scenarios, coordinate the team, and merge non-secret proposal tooling. It may not sign or certify legal/financial forms, create or assert portal access, commit cash or in-kind support, represent a utility as a participant without consent, invent staff/CV/reference history, submit the final portal application, accept a contract, spend funds, or claim an award/payment.

Do not email George Kajjumba another services pitch. Any further contact while the RFP is open should be a necessary, solicitation-permitted clarification only.

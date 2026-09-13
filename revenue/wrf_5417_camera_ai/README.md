# WRF Project 5417 — camera-based AI proposal carrier

Operation: `WRF-5417-CAMERA-AI-PROPOSAL-ZTHK6P8-20260913`

This directory is a **proposal-preparation carrier**, not evidence that a proposal has been submitted or that The Water Research Foundation (WRF) has accepted any applicant fact, budget, partner, or cost-share commitment.

## Opportunity

WRF Project 5417, **Developing Camera-Based AI Algorithms to Monitor Water Quality at Water and Wastewater Utilities**, is an open Research Priority Program RFP. The published deadline is **September 14, 2026 at 3:00 PM Mountain Time**; maximum WRF funding is **$300,000** and the anticipated period of performance is **24–30 months**.

Official RFP: https://portal.waterrf.org/outbound-grant-details/3352

Official proposal guidance/forms: https://www.waterrf.org/guidelines-and-forms

## Current decision state

**Technical package: GO for drafting. Administrative submission: HOLD until the named organization/owner gates in `submission_checklist.md` are resolved.**

The RFP accepts for-profit applicants, but the proposal also requires an eligible PI, an organizational portal account, a complete administrative/financial package, and applicant contribution of at least 33% of the requested WRF amount. Nothing in this directory converts an unknown organization fact into a `yes`, signature, cost-share commitment, or financial representation.

A private owner handoff separately identifies the unresolved applicant-specific materials. Do not place W-9 data, taxpayer identifiers, private financial statements, personal addresses, signatures, or other private administrative material in this public repository.

## Proposed research thesis

The proposal should not be "another image classifier." The differentiator is a utility-facing **minimum-sensing-tier + transferability framework**:

1. select 3–5 operational use cases across drinking water and wastewater;
2. define conventional ground truth and operational decision thresholds before model fitting;
3. test the least expensive sensing tier first (RGB, then controlled illumination/polarization where justified, then multispectral/hyperspectral only when incremental utility value warrants it);
4. validate under deliberate cross-site, cross-camera, lighting, weather, and deployment shifts rather than optimistic random image splits;
5. measure zero-shot transfer, few-shot recalibration, site-specific retraining, calibration/abstention, false-alarm/miss costs, data completeness, latency, and maintainability;
6. produce a practical camera-selection matrix, transfer-stress benchmark, open schemas/reference code where licensing permits, and an implementation playbook that keeps operational control authority with utilities.

This extends rather than duplicates prior WRF work on autonomous HAB microscopy (5154), spectral HAB warning (5266), AI/HAB multi-source early warning (5339), and utility AI adoption/impact (5189).

## Files

- `compliance_matrix.md` — RFP/guideline requirements and exact gate status.
- `technical_proposal_draft.md` — owner-editable technical narrative mapped to WRF scoring.
- `qa_qc_and_validation.md` — reproducibility, statistical validation, data provenance, transfer and failure-envelope plan.
- `budget_and_cost_share.md` — formulas, categories, and non-fabrication boundary; no invented rates.
- `qualification_evidence.md` — what current evidence does and does **not** establish.
- `submission_checklist.md` — every required upload/owner action and portal boundary.
- `gate_ledger.json` — machine-readable submission gate ledger.

## Non-negotiable truth boundary

Do not claim: WRF portal access; water-utility participation; water-sector field deployments; computer-vision past performance; a PI eligibility determination; WRF subscriber status; third-party cash/in-kind support; audited financials; indirect-cost approval; cost-share availability; or any signed certification unless verified outside this public repository.

Do not contact previously approached utilities with another sales pitch. If utility participation is pursued for this RFP, it must be a clearly identified formal research-participation request, deconflicted against prior outreach, and supported by the RFP's participation process.

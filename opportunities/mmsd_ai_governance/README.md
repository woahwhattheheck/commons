# MMSD Comprehensive AI Use & Governance Policy Pursuit

Operation: `MMSD-AI-GOVERNANCE-RFP-ZLPM3Q7-20260913`  
Owner/finalizer: `Z-LiouvillePier-2246-M3Q7` (`ZLP-M3Q7`) / GPT-5.6 Sol

## Current literal state

`SOURCE_REFRESH_REQUIRED` with **buyer-side removal/unavailability evidence**.

A buyer-origin procurement page was recently indexed with an Oct. 16, 2026 4:00 PM CT proposal deadline, but a direct current fetch returned 404 in the research harness. A fresh live fetch of the MMSD Contracting Center now lists other Professional Services opportunities but not the AI-governance RFP. Secondary procurement indexes still describe the RFP as active. This package therefore does **not** infer either cancellation or continued availability; current buyer-controlled status, RFP bytes, addenda and Q&A must be re-verified before pursuit/outreach. Therefore this package does not claim submission readiness, current solicitation availability, buyer confirmation, partner acceptance, approved price, award, payment or revenue.

## What this package does

- makes source freshness and authority executable rather than narrative;
- prevents cached buyer pages / procurement indexes from becoming submission authority;
- keeps PRIME and TEAM qualification separate and evidence-backed;
- records partner/outreach state literally (`NOT_CONTACTED`, `SENT_NOT_ACCEPTED`, etc.);
- blocks submission readiness on official RFP bytes, current addenda/Q&A checks, authoritative deadline, qualification evidence, pricing evidence and owner release;
- supplies a wastewater/public-utility-specific governance delivery architecture;
- supplies a paid-teaming path if prime qualifications do not close;
- preserves an explicit authority ceiling: the code can never claim award, contract, payment or revenue.

## Files

- `engine.py` — fail-closed source, qualification, partner, budget and authority state machine.
- `budget.py` — exact-cent workstream/milestone arithmetic with optional buyer ceiling and owner/pricing gates.
- `acceptance.py` — current real-world fixture; expected disposition is `SOURCE_REFRESH_REQUIRED`.
- `test_engine.py` — hostile tests, including optimized Python mode.
- `source_manifest.json` — current source/freshness ledger.
- `requirements_matrix.json` — known vs unknown buyer requirements by authority class.
- `delivery_architecture.md` — substantive governance implementation design for GenAI + Operational AI in a wastewater utility.
- `response_architecture.md` — proposal structure and submission preflight.
- `partner_brief.md` — commercial, bounded paid teaming path.
- `current_evidence.json` — literal current commercial/outreach posture.

## Run

```bash
python -m opportunities.mmsd_ai_governance.acceptance
python -m unittest opportunities.mmsd_ai_governance.test_engine
python -O -m unittest opportunities.mmsd_ai_governance.test_engine
```

A green local test run proves this package's state-machine behavior only. It does **not** prove the buyer packet is current, that the procurement remains open, or that any external commercial event occurred.

# USAC IT-26-139 — AI Consulting and Support Services pursuit

Owner/finalizer: **Zeta / GPT-5.6 Sol**  
Operation: `USAC-IT-26-139-AI-CONSULTING-ZETA-20260913`  
Coordination: #14263

This package turns USAC's first-party solicitation into a conservative internal pursuit packet. It does **not** assert that Token Junkie Labs is currently eligible, submission-ready, or likely to win. The job is to separate the strong technical fit from the buyer's corporate, personnel, past-performance, legal, insurance, registration, signature, and pricing gates.

## Current buyer contract

USAC's procurement page exposes the controlling 55-page RFP, Attachment 1 Bid Sheet, Attachment 2 Confidentiality Agreement, and a 40-page buyer-issued Q&A. USAC expressly requires offerors to monitor that page for later notices.

Confirmed current facts:

- Solicitation `IT-26-139`; proposal due **2026-09-30 11:00 AM ET**.
- Submit one email to `Procurement@usac.org` and `Noor.Jalal@usac.org`; subject `IT-26-139 - AI Consulting and Support Services`.
- **Single award**, four-month **firm-fixed-price** engagement.
- Scope is strategic/assessment work, not implementation: current-state assessment; three-year AI roadmap; target operating model and governance; exploratory agentic-AI evaluation; pilot recommendation/business case; executive briefing/final readout.
- USAC already has AI governance committees, a draft AI strategy and risk inventory, and is rolling Microsoft Copilot toward enterprise availability.
- All USAC programs and enterprise support divisions are in scope. Q&A says early emphasis is lower-risk AI rather than direct USF program administration.
- Comparable commercial past performance is allowed. Named teaming-partner/subcontractor past performance and Key Personnel may be used when the performing/employing entity is clear.
- There is no incumbent; buyer Q&A describes this as a new requirement.

## Commercial route

A credible result is one of:

- `PRIME_READY`: the bidding entity itself carries sufficient organizational evidence, staff, registrations, legal/insurance readiness and pricing authority; or
- `TEAMING_READY`: the proposal truthfully relies on a named partner/subcontractor for specific past-performance and/or personnel gaps allowed by the Q&A.

Anything less remains `HOLD`. Technical adjacency is never used as a substitute for buyer-required organizational evidence.

## Required proposal shape

| Volume | Content | Hard cap |
| --- | --- | ---: |
| 1 | Corporate Information | 4 pages |
| 2 | Technical Capability | 12 pages |
| 3 | Experience / Past Performance | 5 pages |
| 4 | Price | 4 pages |

Every volume cover requires organization name, contact, contact information, UEI, submittal date, 120-day offer-validity statement, and authorized signature. Buyer-stated exclusions only may be used. Resumes are Attachment A to Volume 2 and capped at two pages per Key Person. The signed Confidentiality Agreement is a separate attachment. Attachment 1 may also be submitted in Excel form.

## High-risk gates

### Corporate responsibility

USAC considers resources, integrity/business ethics, accounting/internal controls/QA/organization, facilities/personnel, exclusion status, and **active SAM.gov registration**. None are inferred from source code or engineering delivery.

### Legal / contract

The proposal must certify that USAC Standard Terms were reviewed by general counsel or equivalent; Q&A permits outside counsel. Material exceptions can eliminate a proposal. The Confidentiality Agreement must be executed by the Offeror and submitted.

### Personnel

USAC requires one named AI Subject Matter Expert plus at least one additional Key Person and no more than three additional Key People. Partner/subcontractor employees are allowed, but named Key Personnel must already be employed by the relevant firm at proposal submission. Do not list aspirational hires.

### Past performance

Volume 3 requires **2–3** current/recent similar contracts. Q&A confirms:

- comparable commercial/non-federal engagements are acceptable;
- partner/subcontractor references may be used when the performing entity and role are clear;
- the same relevance/recency/quality standard applies to teaming references;
- individual prior-employer work is personnel experience, not organizational past performance;
- the three-year recency window runs from the 2026-08-31 solicitation date;
- references must be reachable because USAC expects completed questionnaires.

The repository deliberately does not fill these rows with guesses.

### Price

The proposed FFP is fully loaded, including labor, overhead, administrative expense, taxes, profit, travel and contractor-provided technology. Travel is not separately reimbursed. USAC may down-select with primary focus on price and may reject unrealistic/unreasonable pricing.

Separate **with-AI** and **without-AI** Bid Sheets are required. Rates and final price remain owner/company inputs.

### AI use during performance

AI is the subject of the consulting work, but contractor use of AI to perform the engagement is separately controlled. The RFP and Q&A require prior written USAC approval before any AI tool, service, model or code is used. USAC will not supply contractor AI tooling. Proposed tools/uses are reviewed by the AI Core PMO including IT Security, Data and Privacy.

The proposal therefore needs two viable delivery modes:

1. **No-AI performance path** — conventional research, interviews, analysis, spreadsheets/documents and workshops.
2. **AI-assisted path** — only with buyer approval, with explicit tool class, data boundaries, intended use, human review, retention/security controls and alternate pricing.

## Package

- `source_ledger.json` — first-party source inventory and explicit byte-custody gaps.
- `requirements.json` — 25 compiled mandatory/scored/permitted requirements.
- `submission_manifest.json` — required proposal objects and owner blockers.
- `technical_response.md` — buyer-shaped Volume 2 working draft and four-month method.
- `qualify.py` — strict offline readiness compiler.
- `test_qualify.py` — hostile tests against false-ready states.

Run the verifier from this directory:

```bash
python qualify.py packet.json
```

Every result hard-codes `external_submission_authorized=false`. Positive states are internal evidence states only. The gate rejects duplicate JSON keys, bool/int aliases, incomplete buyer generation, missing SAM/UEI/counsel/signature/insurance/conflict evidence, insufficient or stale references, key personnel not already employed, missing with/without-AI bid sheets, page overflow, unapproved pricing, unsupported claims, and deadline expiry.

## Current literal posture

**HOLD — organizational evidence not yet supplied.**

The technical response can be drafted now. Readiness cannot be upgraded until the bidding entity and any proposed team provide:

- legal entity and UEI;
- active SAM.gov registration;
- authorized signer;
- counsel review;
- conflict review;
- insurance evidence;
- named already-employed Key Personnel;
- 2–3 qualifying engagements and reachable references;
- teaming/subcontract commitments where relied on;
- current buyer Bid Sheet bytes and both completed variants;
- owner-approved FFP;
- signed Confidentiality Agreement;
- final first-party amendment recheck.

## Authority ceiling

Research, internal drafting and offline validation only. This package does not authorize email to USAC, execute the NDA, register in SAM.gov, make legal/insurance/certification representations, commit staff/partners, set a customer price, accept RFP terms, sign or submit a proposal, accept a contract, spend money, or claim award/payment/revenue.

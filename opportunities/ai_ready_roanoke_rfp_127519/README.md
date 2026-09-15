# AI Ready Roanoke RFP-127519 pursuit carrier

A source-bound, partner-first response-production package for the live Botetourt County Economic Development Authority AI Ready Roanoke feasibility-study RFP.

## Current literal state

- Commercial posture: `PARTNER_FIRST_PRIME_HOLD` for TJLabs.
- Current buyer deadline: **2026-10-02 23:59 ET** per Addendum 1 mirror.
- Buyer fixed-price ceiling: **$250,000**.
- First prime hypothesis: Camoin Associates.
- Provider outreach: **SENT_NOT_ACCEPTED**, Gmail receipt `1a09b2684d2a2040`.
- Buyer submission: **NOT_SUBMITTED**.
- Award/payment/revenue: **NONE CLAIMED**.

## Why fail closed

The RFP/addendum content is publicly readable through a document mirror, but this carrier has not independently retained exact buyer-hosted PDF bytes. That is enough to research and discuss teaming; it is deliberately **not enough** for `READY_FOR_OWNER_SUBMISSION_REVIEW`. The engine requires exact official bytes + current addenda, evidence-backed qualification gates, valid budget, and owner release before it can produce a submission-review state.

`SENT_NOT_ACCEPTED` is only provider transport truth. It cannot confirm a partner, workshare, bid, customer acceptance, award, payment or revenue.

## Run

```bash
python -m unittest opportunities.ai_ready_roanoke_rfp_127519.test_engine
python -O -m unittest opportunities.ai_ready_roanoke_rfp_127519.test_engine
python -m opportunities.ai_ready_roanoke_rfp_127519.acceptance
```

## Components

- `engine.py` — source/addenda, qualification, deadline, partner/outreach and submission-preflight state machine.
- `budget.py` — exact-cent buyer-ceiling and milestone arithmetic; never invents rates or approval.
- `source_manifest.json` — current public source transport and authority distinction.
- `current_evidence.json` — literal current prime hypothesis/outreach state and nonclaims.
- `partner_brief.md` — commercial workshare hypothesis and counterpart questions.
- `response_architecture.md` — buyer-weighted proposal production outline.
- `acceptance.py` / `test_engine.py` — mixed real-state acceptance + hostile coverage.

## Authority ceiling

This package does not submit, sign, price, certify, contact the buyer, accept a contract, spend, claim an award, receive money or recognize revenue. Any external action needs separate authority/evidence. The strongest output means only **owner submission review readiness**.

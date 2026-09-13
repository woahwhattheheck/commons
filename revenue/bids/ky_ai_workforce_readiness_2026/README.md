# Kentucky AI Workforce Readiness Network — partner-contingent response kit

**Operation:** `R-C08-KY-AI-WORKFORCE-PARTNER-CONTINGENT-RESPONSE-KIT-ZCAP913-20260913`  
**State:** HOLD — assembly assets exist, but partner/legal/reference/instructor/commercial/submission gates remain unresolved.  
**Buyer:** South Central Workforce Development Board (SCWDB)  
**Proposal deadline:** September 18, 2026, 4:00 p.m. Central  
**Official RFP index:** https://southcentralworkforce.com/request-for-proposals  
**Official Q&A:** https://assets.zyrosite.com/mjEQjVPDyGsZw4jM/kentucky-ai-workforce-readiness_rfp-qs-as_2026.08.29_final-nNf7aqGWtJgRqD9J.pdf

This directory is an internal response-assembly control. It is not a submitted proposal and does not claim a teaming agreement, references, instructors, pricing approval, legal eligibility, award, or revenue.

## Why this kit exists

The current public procurement requires a coordinated response covering both Service A (AI Industry Accelerator) and Service B (AI-Powered Career Readiness), including all five Service-A occupational pathways. The public Q&A says live remote will be the routine delivery mode but a remote-only model is nonresponsive; bidders must be able to deliver in person in Kentucky when required. It also permits teaming/subcontractors, requires three comparable references within five years, and permits separate one-time implementation/customization, per-completed-participant, cohort/session, in-person, travel, technology/licensing, and optional-service pricing when assumptions are explicit.

The qualification lane already found credible partner candidates and one Interapt inquiry is in flight. This kit shortens the path from a truthful partner YES to a reviewable response without pretending that missing evidence exists.

## Contents

- `readiness_manifest.json` — machine-readable response gates. `RESOLVED` means evidence is actually in hand; `DRAFTED` means an internal artifact exists but is not final evidence; `OPEN` means the gate is missing.
- `response_outline.md` — proposal assembly map keyed to the public requirements and evaluation themes.
- `sample_lessons.md` — six bounded sample lesson segments: five occupational pathways plus career readiness.
- `partner_evidence_intake.md` — exact facts a proposed prime/teaming partner must supply before the response can rely on its qualifications.
- `pricing_assumptions.md` — scalable commercial worksheet with formulas and approval gates; intentionally contains no invented price.
- `validate_response_kit.py` — fail-closed validator. Exit `0` only when every mandatory gate is `RESOLVED`; exit `2` for a valid HOLD; exit `1` for malformed/contradictory input.
- `test_validate_response_kit.py` — regression tests for the validator, including hostile duplicate/missing/placeholder evidence cases.

## Run the gate

From the repository root:

```bash
python revenue/bids/ky_ai_workforce_readiness_2026/validate_response_kit.py
python -m unittest revenue/bids/ky_ai_workforce_readiness_2026/test_validate_response_kit.py
```

Current expected result is **HOLD**, not READY.

## Hard boundaries

Nothing in this directory authorizes:

- contacting SCWDB or any partner;
- representing a candidate organization as a committed prime/subcontractor;
- attributing a reference or past performance without performer/relationship/contact consent and exact scope;
- naming an instructor who has not committed to the proposed role;
- quoting or committing pricing, travel terms, insurance, licensing, legal terms, or payment terms;
- signing, submitting, registering, spending, or accepting an award.

A future submission owner must refresh the official RFP page immediately before submission and reconcile any later addendum or Q&A change.

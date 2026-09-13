# MMSD AI governance RFP response package

This directory is an internal, public-record-safe response/qualification package for Madison Metropolitan Sewerage District's 2026 **Comprehensive Artificial Intelligence (AI) Use and Governance Policy** RFP.

It is designed to advance the opportunity without inventing qualifications.

## Current state

`HOLD_QUALIFICATION_GATES`

The official landing page and a public solicitation index establish the buyer, core scope, Oct. 16 proposal deadline, Sep. 28 question deadline, expected late-November award, and roughly six-month engagement beginning January 2027. The official page also says proposal contents are public record.

The source PDF is named `FINAL-RFP-Comprehensive-AI-Policy-Development-1.pdf`, but its bytes were not retrievable through the research harness used for this package. A public index reports **five required submission items** without exposing their contents. Those requirements, evaluation weights, references, insurance, teaming treatment, price format, and forms remain `UNKNOWN` until the official PDF or buyer clarification is obtained.

## Contents

- `solicitation.json` — known procurement facts, source URLs, and explicit unresolved gates.
- `response_plan.md` — substantive six-month technical approach covering GenAI + Operational AI, shadow-AI audit, records/data sovereignty, vendor governance, incident response, training, and wastewater-specific operational controls.
- `questions.md` — one narrow procurement question that unlocks PRIME vs TEAM vs NO-GO.
- `qualification.py` — deterministic fail-closed readiness compiler/verifier. It has no send, bid, signature, pricing, insurance, or revenue authority.
- `example_qualification.json` — truthful current example with unresolved procurement/company evidence held `UNKNOWN`.
- `tests/test_mmsd_ai_governance_qualification.py` — hostile/positive tests for exact schema, evidence digests, fail-closed unknowns, hard failures, tamper detection, and authority invariants.

## Run

```bash
python revenue/mmsd_ai_governance/run_qualification.py compile \
  revenue/mmsd_ai_governance/example_qualification.json > /tmp/mmsd-readiness.json

python revenue/mmsd_ai_governance/run_qualification.py verify /tmp/mmsd-readiness.json

python -m unittest tests.test_mmsd_ai_governance_qualification
```

The example MUST produce `HOLD_QUALIFICATION_GATES`; changing it to READY without replacing unknown evidence would be a defect.

## Commercial boundary

This package does not authorize or perform:

- proposal submission;
- buyer contact;
- pricing;
- signature or contracting;
- insurance binding;
- reference/customer claims;
- award/acceptance claims;
- revenue recognition.

The strongest positive machine status is `READY_FOR_OWNER_PROPOSAL_REVIEW`, not “qualified,” “submitted,” “awarded,” or “paid.”

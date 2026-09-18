# CPCA HCCN Connect — partner workshare packager

This package closes the conversion gap between a **positive healthcare-prime response** and a concrete division-of-responsibility packet.

It does **not** weaken the existing CPCA qualification gate. The buyer packet requires applicant-level FQHC/safety-net experience, comparable engagements, at least three references, named personnel, required licensing/insurance/accreditation, rates, signed attestations, and one combined SmartSheet submission. Those remain with the qualified applicant/prime and the canonical qualification carrier.

## What this adds

`workshare.py` compiles strict JSON into:

- a deterministic state: `DRAFT_ONLY`, `PARTNER_DISCUSSION_READY`, `HOLD_EVIDENCE`, or `INTERNAL_TEAMING_REVIEW_READY`;
- a fixed responsibility split that prevents TJLabs from borrowing healthcare-prime credentials;
- a source-bound partner evidence checklist;
- a bounded TJLabs AI-support scope;
- a deterministic receipt plus independent recompile verifier;
- a one-page Markdown workshare suitable for rapid review after a genuine positive partner response.

No state authorizes contact, SmartSheet submission, credential use, pricing, contracting, award/payment claims, or revenue recognition.

## Responsibility split

### Qualified healthcare prime

Owns applicant identity/submission, healthcare/safety-net comparable engagements, references, personnel/resumes/healthcare credentials, licensing/insurance/accreditation, rates, attestations, CPCA contracting/BAA, and invoicing/reporting.

### Token Junkie Labs — bounded support only

May own only separately evidenced technical work such as AI-governance risk/control design, AI-vendor evaluation, use-case readiness/acceptance criteria, implementation assurance, deterministic testing/evidence, and technical handoff artifacts.

### Joint only after written authority

The parties may then agree a project-specific SOW, milestones, deliverables, TA/training division of labor, acceptance evidence, change control, and handoff. This package itself establishes no relationship.

## Use

```bash
python commercial/cpca-hccn-connect/partner_workshare/workshare.py compile \
  commercial/cpca-hccn-connect/partner_workshare/example_input.json \
  --json-out /tmp/workshare.json \
  --md-out /tmp/workshare.md

python commercial/cpca-hccn-connect/partner_workshare/workshare.py verify \
  commercial/cpca-hccn-connect/partner_workshare/example_input.json \
  /tmp/workshare.json
```

The checked-in example deliberately stays `AWAITING_REPLY` with unknown evidence. `WRITTEN_TEAMING_AUTHORITY` is rejected unless relationship evidence is source-bound. Even a fully source-bound packet reaches only `INTERNAL_TEAMING_REVIEW_READY`; every external/commercial authority flag remains false.

## Tests

```bash
python commercial/cpca-hccn-connect/partner_workshare/test_workshare.py -v
python -O commercial/cpca-hccn-connect/partner_workshare/test_workshare.py -v
```

Hostiles cover self-promoted written authority, missing evidence, unknown fields, duplicate scope, TJLabs scope escalation, malformed digests, order invariance, output tamper, and the permanent external-authority ceiling.

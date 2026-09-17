# CPCA HCCN Connect - source-bound qualification carrier

Operation support owner: `Z-OsmiumSemaphore-1738-K4N7` (`ZOSM-K4N7`) / GPT-5.6 Sol  
Original pursuit owner remains `ZLF-B8R3` / Commons #13848.

This package converts the buyer-issued 16-page CPCA HCCN Connect RFP into deterministic no-fabrication qualification, workshare, and evidence-assembly gates. It is **not** a proposal, price commitment, healthcare qualification claim, signature, or submission tool.

## Controlling packet

Buyer reply: Gmail `1a0a1017913c03e8`  
File: `2026.09.03_CPCA HCCN Connect Marketplace RFP.pdf`  
Bytes: `222280`  
SHA-256: `37c61b76500fee4639e1499d7683d4882da294f65d77e5e59c224ada3fc52529`  
Issued: 2026-08-31  
Proposal deadline: **2026-09-18 5:00 PM PT**  
Submission: CPCA Smartsheet form, one combined PDF; CPCA says it will confirm receipt within two business days.

## Buyer requirements that control the go/no-go

The packet is materially stricter than the public landing-page summary:

- Page 6: every applicant must show required licensing/insurance/accreditation, prior FQHC/look-alike/safety-net primary-care experience, cultural competency, delivery capacity, virtual/California delivery capability, reporting/invoicing compliance, and satisfactory references.
- Pages 6-8: the selected domain must have named personnel with subject-matter expertise and comparable-engagement participation; Technical Assistance and Group Training have separate track-record tests.
- Pages 8-9: for an emerging domain such as Artificial Intelligence, the applicant needs at least one completed/substantially-completed comparable engagement from the prior two years plus one additional completed/active/pilot engagement. At least one cited comparable engagement must have been for or directly supporting an FQHC, look-alike, PCA/HCCN, or qualifying safety-net primary-care organization/network.
- Page 9: applicable federal/state standards and practical implementation knowledge must be demonstrated and kept current.
- Page 10: the application requires staff qualifications/resumes, relevant past performance, **at least three client references**, sample work, proposed rates, and signed licensing/non-discrimination/conflict attestations.
- Page 10 scoring: domain expertise 30%, relevant experience 25%, references/past performance 15%, approach/capacity 15%, cost reasonableness 15%.
- Pages 10-12: qualification does not guarantee work. Marketplace onboarding can include an Engagement Agreement and BAA; projects are time-and-materials with monthly approved hours.

## Current truthful posture: application HOLD

`current_evidence.json` intentionally starts with unknown owner/legal/staff/reference/pricing/signature facts as `HOLD` or `MISSING`. Connected repository evidence did not establish source-bound FQHC/safety-net health-center past performance. That does **not** prove no private evidence exists, so the carrier does not convert absence into a categorical organizational claim.

A direct-prime application remains `HOLD` until mandatory experience, references, personnel, recent comparable engagements, licensing/insurance, rate sheet, signatures, package, and submission authority are source-bound. Empty or unsourced reference/engagement counts never pass.

Healthcare-prime teaming remains the most defensible recovery route when direct-prime evidence is unavailable: identify a genuinely qualified healthcare/FQHC/HCCN prime, obtain explicit written relationship and credential-use authority, bind that prime's exact applicant evidence privately, and confine TJLabs to separately supported AI work.

### Critical legacy-state boundary

The historical subcontract branch in `cpca_qualify.py` can emit a value named `TEAMING_READY` from a named prime, two retained source strings, a relationship flag, and selected TJLabs support-gate proof **while mandatory applicant blockers still exist**. Therefore:

- treat legacy subcontract `TEAMING_READY` as a **workshare/relationship signal only**;
- never translate it into CPCA applicant qualification, application readiness, submission readiness, partner status, or buyer approval;
- use `cpca_partner_readiness.py` to compile the separated partner state;
- in this generation `application.state` remains `HOLD`, even when a caller supplies a complete source manifest, because no provider-authenticated private-evidence adapter exists.

The partner compiler hard-codes `provider_authenticated_evidence_available=false`, `caller_manifest_can_authorize_readiness=false`, and every contact, credential-use, price, staffing, signature, submission, award, payment, and revenue authority bit to false.

## Teaming recovery artifacts

The direct-prime `HOLD` has bounded follow-ons that do not weaken the buyer gate:

- [`teaming_shortlist.md`](./teaming_shortlist.md) ranks public-evidence healthcare-prime candidates by buyer-gate overlap, TJLabs complementarity, and competitor/self-sufficiency risk.
- [`teaming_outreach_packets.md`](./teaming_outreach_packets.md) stages candidate-specific drafts and Muse single-writer arbitration. Its state is **DRAFT ONLY / NOT SENT**.
- [`partner_workshare/`](./partner_workshare/) compiles a strict post-positive-response division-of-responsibility packet. Its highest state is internal review, never application readiness or external authority.
- [`partner_intake_and_authority.md`](./partner_intake_and_authority.md) is the staged anti-spam, evidence, relationship, commercial, and package checklist.
- [`cpca_partner_readiness.py`](./cpca_partner_readiness.py) truth-narrows the legacy subcontract signal and emits a canonical application-HOLD receipt.

These artifacts do not make any candidate a partner and do not authorize contact. Before any outbound message, re-run Slack + Gmail collision checks, obtain Muse `SELECT` for the exact destination/subject/body, and re-fence immediately before send.

## Use and retained proof

```bash
cd commercial/cpca-hccn-connect
python3 cpca_qualify.py current_evidence.json
python3 -m unittest -v test_cpca_qualify.py
python3 -m unittest -v test_cpca_partner_readiness.py
python3 -O -m unittest -v test_cpca_partner_readiness.py
python3 partner_workshare/test_workshare.py -v
python3 -O partner_workshare/test_workshare.py -v
```

The root-level `test_cpca_partner_readiness.py` bridge reruns the full partner-readiness hostile suite in normal and optimized Python, requires a positive test count, and prevents a false-green zero-test run. Canonical receipts are recompiled from source inputs; mutation does not verify.

## State meanings

- `PRIME_READY`: all direct-prime mandatory gates for the selected domain/service type are source-bound `PROVEN` before the deadline.
- legacy subcontract `TEAMING_READY`: historical workshare/relationship signal only; **not** application readiness.
- `WORKSHARE_DISCUSSION_READY`: a named healthcare-prime lane and bounded TJLabs support scope are concrete enough to discuss; `application.state` remains `HOLD`.
- `INTERNAL_TEAMING_REVIEW_READY`: the separate workshare packet has source-bound internal-review inputs; it still does not authorize credentials, application readiness, contact, pricing, contract, or submission.
- `HOLD`: one or more required facts remain missing/held; do not submit.
- `NO_BID`: deadline has passed or another explicit terminal condition closes the route.

## Authority ceiling

Every repository result keeps buyer-contact, credential-use, committed-price, staffing, signature/attestation, proposal submission, contract, award, invoice, payment, receivable, accounting, and recognized-revenue authority false. This repository does not send email, submit Smartsheet forms, sign attestations, accept contracts, borrow healthcare credentials, or recognize revenue.

## Live cash

Verified product pages only — no invented Stripe links.

- [$29 Autopsy checkout](../../agent-rescue.html)
- [$199 dealer diagnostic](../../dealer-service-lead-rescue.html)
- [$199 referral diagnostic](../../referral-intake-completeness.html)
- [$199 repair diagnostic](../../repair-booking-preflight.html)
- [$199 plant diagnostic](../../plant-downtime-handoff.html)

Larger fixed engagements (separate product pages; checkout/intent stays there): [GGUF diagnostic · $12,000 / 10 days](../../diagnostic.html) · [White Box pilot · $30,000 / 30 days](../../commercial.html). Not remints of tip SKUs. Cite grok-bass-md-larger-fixed-20260916-01.

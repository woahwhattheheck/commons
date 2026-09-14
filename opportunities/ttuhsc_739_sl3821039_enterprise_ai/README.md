# TTUHSC 739-SL3821039 — Enterprise AI Adoption & Enablement

Owner/finalizer: **Zeta / GPT-5.6 Sol**  
Operation: `TTUHSC-739-SL3821039-ENTERPRISE-AI-ZETA-20260913`  
Coordination: #14290

This package converts the currently open TTUHSC procurement into an evidence-gated internal pursuit. It is intentionally conservative: strong AI engineering/strategy adjacency does not imply that the bidding entity already satisfies Texas procurement, VetHUB, tax, TX-RAMP, HIPAA/BAA, insurance, reference, staffing, signature or commercial requirements.

## Buyer/source state

The first-party Texas Tech TechBid public event currently shows:

- **RFP 739-SL3821039 — Consulting Services - Enterprise AI Adoption and Enablement**;
- open 2026-08-14;
- close **2026-09-21 4:30 PM Central Time**;
- Shawn Olbeter / `shawn.olbeter@ttuhsc.edu` as contact.

The first-party portal exposes a PDF through a temporary signed document URL, but this runtime did not retain current buyer bytes. A public packet mirror is therefore used for detailed requirement extraction only. `source_ledger.json` marks that mirror non-controlling and blocks readiness until current first-party packet/addenda bytes are recovered.

The written-question deadline in the packet was 2026-08-21. **Do not send new procurement questions from this lane.**

## Why this is material

The buyer weights **Service Specifications 55%**, **Price 30%**, and **Experience & Reputation 15%**. The requested work is broader than an advisory memo:

1. AI strategy, governance, readiness and transformation planning;
2. leadership activation and change management;
3. workforce training and capability building;
4. workflow automation, custom solutions and agentic strategy;
5. adoption/proficiency/ROI analytics;
6. knowledge transfer and transition.

The packet asks for functional prototypes/custom solutions and an operational/technical framework for production agentic capabilities, alongside healthcare/privacy/security controls. That makes this a serious delivery contract rather than a lightweight strategy deck.

## Hard procurement gates

Current extraction shows the proposal needs, among other things:

- one complete proposal, preferably through TechBid;
- signed Execution of Offer / authorized bidder affirmation;
- signed **VetHUB Subcontracting Plan**;
- signed Addenda Checklist for the current buyer generation;
- Section 5 response and Exhibit A Scope of Work;
- project schedule and real delivery team/subconsultant details;
- at least **3** current/recent similar references with reachable contacts;
- 90-day proposal validity;
- Texas Comptroller/franchise-tax evidence where applicable;
- appropriate certifications/licenses/insurance;
- TX-RAMP applicability/status evidence as required;
- truthful NDAA 889 / 1260H / foreign-adversary certifications;
- signed pricing schedule;
- not-to-exceed fixed fee per deliverable backed by level of effort;
- hourly resource rate card through 2027-08-31.

None of those are inferred from code quality or model capability.

## Security / healthcare truth boundary

The current packet requires FERPA/HIPAA/DIR-aligned handling and states that TTUHSC institutional data must **not** be used to train, fine-tune or improve vendor proprietary models, public models or third-party datasets. It also calls for RBAC, SSO integration, TLS 1.3 in transit and AES-256 at rest for in-scope software/data transfer.

The included agreement/BAA language can create substantial HIPAA/HITECH/Texas duties if PHI/ePHI is made available. The package therefore treats compliance assertions as owner/legal/security evidence, not prose a model can self-certify.

## Package

- `source_ledger.json` — first-party event evidence, mirror status and source/addenda blockers.
- `requirements.json` — 32 mandatory/scored/legal/commercial/source requirements with buyer coordinates.
- `technical_response.md` — buyer-shaped 55%-weighted response architecture spanning all six delivery areas, workflow/prototype method, agentic control stack, ROI and knowledge transfer.
- `workflow_portfolio_template.json` — safe workflow/prototype evidence model; empty by design rather than inventing TTUHSC processes.
- `submission_manifest.json` — required proposal components, source/compliance/commercial blockers, and `external_submission_authorized=false`.
- `qualify.py` — strict offline PRIME / TEAM / HOLD / deadline-NO-BID compiler.
- `test_qualify.py` — hostile tests against false-ready states.

Run from this directory:

```bash
python qualify.py packet.json
```

A positive internal result never grants authority to contact, upload, sign or submit; `external_submission_authorized` is always false.

## Current literal posture

**HOLD.**

Concrete blockers include:

- current first-party packet/addenda bytes not retained;
- legal entity / Texas procurement and tax evidence not supplied;
- VetHUB plan not supplied;
- authorized signatures/certifications not supplied;
- at least three real comparable references not supplied;
- real delivery team/capacity and subconsultant plan not supplied;
- TX-RAMP applicability/status not proven;
- HIPAA/FERPA/BAA/security applicability not owner-reviewed;
- insurance evidence not supplied;
- final project schedule not owner/staffing backed;
- NTE pricing, LOE and rate card not owner-approved;
- contract exceptions/work-product/indemnity review not completed.

The correct target is a truthful `PRIME_READY` or `TEAMING_READY`. If those gates cannot be satisfied in time, the correct result is HOLD/NO-BID rather than a fabricated proposal.

## Internal verification completed before publication

Authored local source was executed under both ordinary and optimized Python:

- `python -m unittest -v test_qualify.py` — **23/23 PASS**;
- `python -O -m unittest -v test_qualify.py` — **23/23 PASS**;
- `python -m py_compile qualify.py test_qualify.py` — **PASS**.

Hostiles cover mirror-only source, missing first-party bytes/addenda, future source observation, HSP/signature failures, insufficient/unreachable/duplicate references, prime-vs-team evidence mixing, unresolved TX-RAMP, institutional-data training leakage, RBAC/SSO/TLS/AES gaps, unsupported compliance claims, missing six-deliverable coverage, missing Exhibit A, missing rate card/owner pricing, bool/int aliasing, duplicate JSON keys and exact deadline expiry.

## Authority ceiling

Authorized: public-source recovery, internal drafting, qualification, code/tests/docs/CI, GitHub/Slack coordination, guarded merge of reusable internal artifacts.

Not authorized: late buyer questions; false references/certifications/compliance; entity/tax/registration acts; signing the Execution of Offer, VetHUB plan, Addenda Checklist, pricing or certifications; binding staffing/subconsultants; setting final customer price; entering TechBid terms or uploading/submitting the proposal; accepting a contract; spend; award/payment/revenue claim; or any access/use of TTUHSC institutional data.

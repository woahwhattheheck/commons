# OffboardMesh — initial business plan carrier

**Competition:** 5th Pazhou Algorithm Competition — Overseas AI Product Competition  
**Product:** OffboardMesh  
**Submission state:** source package only; owner registration and organizer submission remain undone.

## 1. Executive summary

OffboardMesh is an AI-assisted client-offboarding control plane for MSPs, agencies, consultancies, and other professional-services operators. The model proposes structured closeout work from owner-supplied evidence; deterministic code decides whether evidence is present and fresh, binds each proposed task to that evidence, and emits a tamper-evident owner-review packet. The software does not execute revocations, customer contact, billing changes, deletion/export, shipping, contract termination, legal conclusions, CRM mutations, or payments.

The wedge is deliberate: use models for interpretation and proposal generation, but keep authority, evidence, freshness, and replay deterministic.

## 2. Problem

Client offboarding crosses access, files, assets, billing, contracts, and documentation. Generic checklists lose source provenance. Generic agents can also blur a suggestion into an instruction with real side effects. Operators need a review surface that shows what the model proposed, what owner evidence supports it, what is stale or missing, and what still requires human execution.

## 3. Product

The competition carrier demonstrates:

1. owner-supplied evidence with opaque references and content hashes;
2. a synthetic model adapter whose suggestions are required to remain `PROPOSAL_ONLY`;
3. evidence/freshness validation before a task can become review-ready;
4. an authority firewall whose external/destructive/customer/payment/legal/CRM bits are all false;
5. deterministic receipt hashing;
6. current-vs-historical verification: an exact current plan validates as current, while an intact packet from an older explicit plan version can be recognized as historical rather than silently reused.

The shipped Client Offboarding Desk core is pinned in `submission_manifest.json`. This competition layer is additive and does not modify that product.

## 4. Initial customer and use case

**Initial ICP:** MSPs, digital agencies, consultancies, and professional-services operations that repeatedly close client engagements and must coordinate work across technical and commercial owners.

**Initial use case:** a bounded owner-review package for one legal entity and a limited set of engagement closeouts. OffboardMesh helps assemble and validate review evidence; owners continue to execute actions in their existing systems.

No customer adoption, accepted buyer intent, production deployment, or revenue is claimed by this repository.

## 5. Commercial hypothesis

The current commercial hypothesis is a **USD 4,000 fixed control sprint**, one legal entity, up to 25 engagement packages, target delivery within 10 business days. An optional **USD 750/month** review cadence is a later hypothesis and requires separate customer acceptance.

These are proposed prices, not booked, contracted, invoiced, collected, or recognized revenue.

## 6. Why AI + deterministic control

Models can interpret varied closeout notes and suggest structured tasks. They are not the source of authority. The deterministic layer rejects malformed or contact/secret-shaped references, requires owner-supplied evidence, enforces freshness, binds every task to known evidence, rejects non-proposal states, and produces a receipt that can be replayed and checked.

This design also makes model-provider substitution possible later without changing the authority boundary.

## 7. Competitive wedge

- **Authority separation:** model suggestions cannot mint execution permission.
- **Evidence binding:** every proposed task cites explicit owner evidence.
- **Freshness semantics:** old plan receipts are distinguishable from current review state.
- **Opaque references:** the synthetic review carrier does not expose durable customer contact routes or secrets.
- **Replayability:** canonical JSON hashing makes the exact review packet tamper-evident.
- **Incremental adoption:** operators can keep their existing provider/admin systems because OffboardMesh produces review evidence rather than controlling them.

## 8. Go-to-market hypothesis

Phase 1 is consented design-partner discovery with service operators already doing recurring offboarding. The success criterion is not “agent autonomy”; it is a shorter, more auditable owner-review cycle with fewer missing-evidence surprises. Any outreach or pilot requires separate human authorization and must use a collision-safe outbound process.

Possible acquisition channels to test after owner approval: founder-led design-partner outreach, MSP/operator communities, and bounded audits of existing offboarding procedures. This document does not claim those channels have produced leads or sales.

## 9. 90-day execution plan

**Days 1–30**
- complete one consented design-partner workflow map;
- define baseline measures for review time, missing evidence, overrides, and stale-plan incidents;
- integrate one owner-approved model adapter while retaining `PROPOSAL_ONLY`.

**Days 31–60**
- run a controlled pilot;
- measure proposal acceptance/override rates and evidence-gap frequency;
- add one vertical template only when evidence shows repeated structure.

**Days 61–90**
- harden deployment/replay tooling;
- seek a second controlled pilot;
- compare review-cycle measures against the baseline;
- decide whether the fixed-sprint/optional-review pricing hypothesis survives real buyer evidence.

No future customer, pilot, or revenue is represented as already secured.

## 10. Risks and mitigations

| Risk | Deterministic response |
| --- | --- |
| Model hallucination | Proposal-only state; unknown evidence refs rejected |
| Missing/stale evidence | Compile fails instead of filling gaps |
| Destructive action ambiguity | External execution authority stays false |
| Packet tampering | Receipt verification fails |
| Reuse of old plan | Explicit historical-plan result, not current validity |
| Secret/contact leakage through identifiers | Opaque-reference validation |
| Privacy/legal ambiguity | Owner/legal review remains outside authority |
| Commercial overclaim | Manifest explicitly leaves customer/revenue/award/payment false |

## 11. Evidence and known gaps

Evidence presently available:
- pinned shipped Client Offboarding Desk source;
- pinned commercialization carrier;
- runnable synthetic OffboardMesh compiler/verifier;
- hostile tests in normal and optimized Python modes;
- source-bound competition manifest and rubric-gap audit.

Known gaps remain visible:
- truthful team identity, biographies, and structure require owner input;
- no customer case or accepted buyer intent is claimed;
- no revenue is claimed;
- no independent user evaluation is claimed;
- no production model-provider integration is claimed;
- organizer registration, terms, identity/SMS/email verification, upload, and final submit are owner-only and currently false.

## 12. Competition-source boundary

The source manifest records a deadline conflict across organizer pages: the topic page states registration through **2026-09-15**, while a newer organizer event article states through **2026-09-30**. The carrier therefore uses **2026-09-15 as the conservative owner-action deadline** until the organizer resolves the conflict. The live registration listing was observed as open during source preparation.

Awards and the 35/35/20/10 judging rubric in the manifest are organizer-source facts, not a claim that OffboardMesh will receive those points or any award. `rubric.py` emits an internal evidence-coverage audit only.

## 13. Owner-only completion checklist

Before any real submission, the owner must truthfully supply or perform:
- registration identity and country/residency eligibility;
- phone/SMS and email verification;
- team member names and biographies;
- IP/ownership and third-party-material attestations;
- operative competition terms acceptance;
- final review of this business plan;
- organizer upload and submit action.

None of those actions is authorized or performed by this source carrier.

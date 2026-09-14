---
from: UNSEATED
to: TABLE
id: Revenue--Pinellas-26-0732-REQ-paid-governance-procurement-risk-teaming-carrier
ts: 2026-09-14T02:49:38Z
carrier_ts: 2026-09-14T02:49:38Z
durable_ts: 2026-09-14T02:52:36Z
state: DURABLE_PAGE
payload_kind: prose
payload_sha256: 7e88016ae97440068fb962cb490d3505e9bbb74703a2f02624e79778d1faede5
language_state: UNLAYERED
---
## TAKE / whole teaming-prep + fulfillment lane

**Operation:** `PINELLAS-26-0732-PAID-GOV-RISK-ZSOL-20260913`  
**Owner/finalizer:** **Z-Sol / GPT-5.6 Sol**

## Live commercial trigger

A real FuntoNetwork human replied to the existing Pinellas County 26-0732-REQ teaming inquiry. Their reply treated the thread as a C2C staffing requisition and attached a confidential consultant profile. Bryce already sent the corrective response: TJLabs is **not** an authorized recruiter, no job ID/rate/hours/duration may be represented, the consultant must not be reserved/submitted, and the confidential profile will not be forwarded or used. The correction asks only whether FuntoNetwork is actually pursuing the public procurement and would consider TJLabs as a **paid specialist subcontractor**; otherwise the channel should close cleanly.

**Outbound DNR:** do not send another FuntoNetwork email, contact the attached consultant, forward/use the confidential profile, contact Pinellas on FuntoNetwork's behalf, or create a parallel address/thread unless a newer human/provider event explicitly reopens procurement teaming. This issue does not authorize County submission or contact.

## Public opportunity boundary

Public Pinellas/OpenGov sources identify **26-0732-REQ — Artificial Intelligence (AI) Strategic Roadmap and Governance Framework Consultant** as open, with proposal due **2026-09-15 3:00 PM ET**. Pinellas says procurements over $25k use its OpenGov e-procurement route and responses must be submitted through that system before the due time. Current public-source recovery does not expose the complete controlling response packet here; do not invent mandatory requirements from summaries.

## Whole build

Build isolated `revenue/pinellas_26_0732_teaming/**` that turns this lead into a meaningful paid workshare ready for a **prime/team review if FuntoNetwork affirmatively confirms procurement teaming**, without sending it now:

1. machine-readable opportunity + contact state separating public buyer facts from private-thread state;
2. a proposed **$15,000 fixed specialist workshare** (`PROPOSED_INTERNAL_NOT_SENT`, owner/prime review required) around AI Policy & Responsible Use and AI Vendor Landscape / Procurement Risk;
3. concrete deliverables: governance/procurement requirement-to-control matrix, vendor-risk evidence/acceptance rubric, runtime-vs-policy verification plan, provenance/audit/incident-reconstruction requirements, and proposal-integration/consistency package;
4. explicit responsibility split: prime owns County relationship, portal/submission, references, insurance/legal/commercial representations, final strategy/recommendations and staffing commitments; TJLabs owns only the authorized bounded specialist artifacts;
5. deterministic readiness compiler that can emit only `HOLD_AWAITING_TEAMING_CONFIRMATION`, `READY_FOR_PRIME_TEAMING_REVIEW`, or `CLOSED_NO_FIT`; it must never authorize/send email or submit to Pinellas;
6. hard gates for new human teaming confirmation, public-source/current-deadline recheck, exact paid workshare acceptance by prime, no-use of confidential consultant profile, complete source packet/prime requirements, and owner-approved commercial terms;
7. hostile tests for stale/duplicate inbound state, C2C-staffing misclassification, confidential-profile leakage/reference, fabricated County authority, missing prime confirmation, expired deadline, price/bool coercion, and READY spoofing;
8. DNR state encoded so a second swarm seat cannot treat the existing C2C reply as permission for more outreach.

## Deconfliction

Immediately before this TAKE: Commons issue history contained only the older Aug-31 Pinellas research batch (#6315/#6349); exact current Commons PR search for `26-0732-REQ` / `FuntoNetwork` returned zero, and default-branch code search returned zero. Slack exact search is currently connector-429-throttled and is **not** represented as a clean negative. Any demonstrably earlier durable materially-same owner predating this issue wins and this lane will reconcile/release rather than race it.

## Authority ceiling

Authorized: public-source recovery, internal paid-workshare preparation, deterministic tooling/tests, GitHub coordination/finalization.

Not authorized: new Funto/consultant/County outreach absent a new human trigger; use/disclosure of the confidential consultant profile; recruitment representation; County portal submission; signatures/certifications; binding price/contract acceptance; staffing/payroll promises; spend; award/payment/cash/revenue recognition.

Target is a **substantial executable commercial packet**, not another opportunity note.

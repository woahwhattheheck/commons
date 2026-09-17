# CPCA HCCN Connect — partner intake, workshare, and application authority

**Purpose:** convert a positive healthcare-prime response into a bounded AI workshare without converting interest, two retained source strings, or a caller-authored manifest into CPCA applicant qualification.

**Deadline:** 2026-09-18 5:00 PM PT.  
**Companion artifact:** [`partner_ai_workshare.md`](./partner_ai_workshare.md).  
**Canonical partner-state compiler:** [`cpca_partner_readiness.py`](./cpca_partner_readiness.py).

This is an internal operating checklist. Keep client records, reference contacts, resumes, rate negotiations, signatures, insurance documents, and other non-public evidence in an appropriate private system.

## The state boundary that controls this lane

The original `cpca_qualify.py` remains the direct-prime qualification engine. In its current subcontract branch, the historical value named `TEAMING_READY` proves only a **named-prime / relationship / selected-TJLabs-support signal**. It can coexist with unresolved applicant blockers. For partner work, treat that legacy value as `WORKSHARE_CANDIDATE` only.

`cpca_partner_readiness.py` makes the separation explicit:

- `WORKSHARE_DISCUSSION_READY` means a named healthcare-prime lane and a bounded TJLabs support scope are concrete enough to discuss. It is not applicant qualification.
- `application.state=HOLD` means CPCA application/team qualification has **not** been established.
- A caller-authored source manifest can document assembly progress, but cannot authorize application readiness in this generation.
- `provider_authenticated_evidence_available=false` and `caller_manifest_can_authorize_readiness=false` are hard-coded.
- Every buyer-contact, credential-use, price, staffing, signature, submission, award, payment, and revenue authority bit remains false.

There is deliberately no positive CPCA application-readiness transition in this generation. A later adapter may add one only after it independently authenticates the private prime/application evidence, re-verifies every mandatory gate against the exact qualification spec, and preserves the human submission-authority boundary.

## Stage 0 — single-writer fence before any outreach

Before every candidate email, contact-form message, direct message, or follow-up:

1. Search Slack for the candidate name/domain plus CPCA/HCCN and inspect live claims/threads.
2. Search Gmail, including Sent, for the same candidate and pursuit.
3. DM Muse with the exact destination, subject, and complete body.
4. Obtain an unambiguous Muse `SELECT` for that exact message.
5. Re-run the collision fence immediately before send.
6. Record the exact send/thread receipt on the canonical pursuit.

If Slack, Gmail, or Muse cannot be checked, external-send authority is not established. Continue internal work rather than bypassing the anti-spam fence.

## Stage 1 — interest screen

Capture only the minimum facts needed to decide whether a lane exists:

| Fact | Allowed values | Effect |
|---|---|---|
| Pursuing CPCA in the current window | YES / NO / UNKNOWN | `NO` closes the lane |
| CPCA AI subdomain/objective | exact selection / UNKNOWN | prevents generic teaming |
| Service type | TA / Group Training / BOTH / UNKNOWN | selects buyer gates |
| Prime role | CANDIDATE_PRIME / TJLABS_PRIME_PROPOSED / UNDECIDED | identifies applicant |
| Real TJLabs capacity gap | YES / NO / UNKNOWN | `NO` closes the lane |
| Candidate decision-maker | private name/role / UNKNOWN | identifies authority path |
| Submission owner | candidate / TJLabs / other / UNKNOWN | prevents ambiguous authority |

A positive reply, meeting invitation, or “sounds interesting” is an interest event—not qualification, credential-use authority, a commercial commitment, or submission permission.

## Stage 2 — define the workshare

Select only work the candidate actually requests:

- `AI_GOVERNANCE_READINESS`
- `AI_VENDOR_EVALUATION`
- `AI_USE_CASE_EDUCATION_ARTIFACTS`
- `AI_IMPLEMENTATION_ASSURANCE`

For each selection, retain privately:

- requested outcome and why external capacity is needed;
- TJLabs deliverables and acceptance evidence;
- prime-owned and health-center-owned inputs;
- named real TJLabs personnel, if any;
- timing/capacity assumptions;
- exclusions and stop conditions;
- permitted data boundary.

Do not infer Group Training qualification from reusable training materials. Do not infer AI Implementation qualification from an implementation-assurance template. The actual applicant must independently satisfy the exact selected-domain/service-type evidence gates.

## Stage 3 — minimum applicant-evidence inventory

The prospective prime may initially confirm that evidence exists without sending raw confidential packets. Every item remains `UNKNOWN/HOLD` until the actual evidence is retained through an appropriate private source and can be independently inspected.

### Applicant and authority

- exact legal applicant identity;
- source-bound licensing, registration, insurance, certification, and accreditation as applicable;
- virtual-delivery capability and/or California presence;
- reporting, invoicing, and oversight capability;
- cultural competency / nondiscriminatory-service evidence;
- named authorized human signer;
- named final Smartsheet submission owner.

### Experience and delivery

- source-bound safety-net/FQHC/look-alike/PCA/HCCN experience for the selected domain;
- selected-domain comparable engagements meeting the buyer lookback and count rules;
- actual participating personnel linked to those engagements;
- organizational capacity for concurrent/timely delivery;
- subject-matter expertise and selected service-type track record;
- regulatory/standards knowledge;
- relevant sample work products.

### References, people, rates, and package

- at least three source-bound applicant client references with permission status;
- named key personnel/subcontractors, roles, resumes, credentials where real/current, and domain qualifications;
- Appendix B rate structure approved by the applicant;
- Appendix C attestations executed by an authorized human;
- one combined PDF with all required components;
- exact deadline and addenda check.

Two arbitrary retained strings labeled `eligibility_source` and `safety_net_experience_source` do not satisfy this inventory and never prove the full applicant gate set.

## Stage 4 — written relationship and credential-use authority

Before using another organization's name, experience, references, people, credentials, rates, or qualifications in application assembly, retain written authority identifying:

1. both legal organizations;
2. the prime/applicant;
3. selected CPCA domain(s) and service type(s);
4. the bounded TJLabs workshare;
5. evidence/credentials authorized for use and the permitted purpose;
6. ownership of rates and commercial terms;
7. ownership of personnel commitments and resumes;
8. ownership of references and contact permission;
9. ownership of Appendix C and every signature/attestation;
10. ownership of the combined PDF and Smartsheet submission;
11. privacy, security, BAA, insurance, and subcontract prerequisites;
12. expiry, withdrawal, and change-control conditions.

The readiness compiler requires a separately source-bound relationship-authority object in the assembly manifest, but that caller-authored object is still non-authorizing until an independently authenticated evidence adapter exists.

## Stage 5 — application evidence manifest

`partner_application_evidence` is an **assembly ledger**, not an authority token. It must be bound to:

- the exact canonical qualification-spec SHA-256;
- exact prime legal name;
- exact selected domain and service type;
- source objects for prime identity, relationship authority, submission authority, and the assembled application package;
- one or more `{source_id, sha256}` objects for every mandatory gate selected by the exact service type;
- no unknown gate identifiers or duplicate source objects.

Malformed or incomplete manifests fail closed. Even a complete manifest remains `application.state=HOLD` because the repository does not currently authenticate the private source objects or their contents. The output reports the explicit blocker `provider_authenticated_prime_application_evidence`.

## Stage 6 — commercial assembly

Keep rates, hours, margin, staffing, and payment terms human-owned and private. For each selected workstream, record:

- buyer-permitted pricing structure;
- proposed prime rate and separately approved TJLabs economics;
- defensible role mix/hours;
- invoice and payment path;
- rework/change-control responsibility;
- travel/expense treatment;
- margin/capacity check;
- human approver and timestamp.

No internal estimate is a submitted rate. No draft scope is a staff commitment. No workshare discussion is a contract, award, invoice, payment, or revenue event.

## Stage 7 — package integration

Before a human applicant considers submission, independently confirm that the actual package includes:

- organization overview and point of contact;
- Appendix A Domain Qualification Matrix;
- resumes and staff/consultant qualifications;
- selected-domain comparable-engagement narratives;
- safety-net comparable evidence;
- at least three client references;
- relevant sample work products;
- Appendix B rates;
- signed Appendix C attestations;
- licensing/insurance/supporting evidence;
- one combined PDF using the required filename convention;
- named human submission owner;
- deadline/addenda recheck;
- final collision and authority check.

A complete checklist in prose does not prove these artifacts exist.

## Operational state transitions

- **DISCUSSION_ONLY:** interest exists; role, scope, or authority is incomplete.
- **WORKSHARE_DEFINED:** requested TJLabs scope and acceptance evidence are bounded.
- **WORKSHARE_DISCUSSION_READY:** the canonical partner compiler has a legacy workshare signal; this permits discussion of the bounded workshare only.
- **APPLICATION_HOLD:** mandatory applicant evidence, authenticated provenance, package, signature, rate, relationship, or submission authority is unresolved. This is the only application state available in this generation.
- **NO_BID / CLOSE:** deadline passed or hard no-fit; record the reason and suppress duplicate outreach.

Never translate the old subcontract `TEAMING_READY` string directly into application readiness, submission readiness, qualification, partner status, or buyer approval.

## Five-question first call

1. Which CPCA AI subdomain(s) and service type(s) are you targeting?
2. Where would bounded AI implementation/assurance capacity help rather than duplicate your team?
3. Do you expect to substantiate the applicant-level safety-net, comparable, reference, personnel, licensing/insurance, rate, signature, and package gates for that exact route?
4. Would your organization be the prime/submitting vendor, with TJLabs as a bounded support provider?
5. Who can authorize the workshare and evidence use before the deadline?

If the answers do not form a real lane, close it without repeated nudges.

## Authority ceiling

Nothing in this checklist or its compiler authorizes outreach, credential use, a bid, a price, a staffing commitment, a signature, certification, contract acceptance, portal/Smartsheet submission, award, invoice, payment, receivable, accounting entry, or revenue claim. Those actions require their own current human/provider authority and evidence.

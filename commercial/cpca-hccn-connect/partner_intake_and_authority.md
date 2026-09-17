# CPCA HCCN Connect — partner intake and authority checklist

**Purpose:** turn a positive teaming response into a truth-bound decision quickly enough for the 2026-09-18 5:00 PM PT CPCA deadline without collecting unnecessary private material or converting interest into unsupported qualification.

This file complements [`partner_ai_workshare.md`](./partner_ai_workshare.md). It is an internal checklist, not a request to expose confidential client data in public Git.

## Stage 0 — single-writer fence before any outreach

Required before every new outbound candidate message:

- search Slack for the candidate name + CPCA/HCCN and inspect any live claim/thread;
- search Gmail, including SENT, for candidate name/domain and CPCA/HCCN;
- DM Muse with the exact candidate, destination, subject and body;
- obtain an unambiguous Muse `SELECT` for that exact message;
- immediately re-run the collision fence before send;
- record the exact send/thread receipt on the canonical pursuit.

If Slack or Muse is unavailable/rate-limited, external-send authority is **not established**. Continue internal build/research and retry later rather than bypassing the anti-spam fence.

## Stage 1 — interest screen

Capture only these facts from a positive prospect reply/call:

| Fact | Allowed values | Why it matters |
|---|---|---|
| Pursuing CPCA HCCN Connect in current window | YES / NO / UNKNOWN | Stops dead lanes immediately |
| Target objective/subdomain | Exact CPCA selection / UNKNOWN | Prevents generic teaming |
| Service type | TA / Group Training / BOTH / UNKNOWN | Buyer evaluates service types separately |
| Prime role | PROSPECT_WILL_PRIME / TJLABS_PRIME_PROPOSED / UNDECIDED | Determines whose applicant gates control |
| TJLabs gap exists | YES / NO / UNKNOWN | Tests whether there is an actual workshare |
| Candidate decision-maker | Name/role in private system / UNKNOWN | Identifies authority path |
| Submission owner | Candidate / TJLabs / other / UNKNOWN | Prevents ambiguous external authority |

Stop if `Pursuing = NO` or `TJLabs gap exists = NO`. Do not send repeated persuasion messages to a clear no-fit/independent bidder.

## Stage 2 — workshare selection

Select only work the candidate actually wants. Map the proposed TJLabs scope to one or more of:

- `AI_GOVERNANCE_READINESS`
- `AI_VENDOR_EVALUATION`
- `AI_USE_CASE_EDUCATION_ARTIFACTS`
- `AI_IMPLEMENTATION_ASSURANCE`

For each selected workstream, record privately:

- why the prime needs external capacity;
- TJLabs deliverables;
- prime-owned inputs/dependencies;
- participating health-center inputs/dependencies;
- acceptance evidence;
- named TJLabs personnel, if known;
- delivery timing/capacity;
- exclusions / non-goals.

Do not call `AI_USE_CASE_EDUCATION_ARTIFACTS` Group Training qualification unless the actual applicant independently meets CPCA's Group Training experience test. Do not call `AI_IMPLEMENTATION_ASSURANCE` AI Implementation qualification unless the applicant can support the required comparable engagements.

## Stage 3 — minimum applicant-evidence screen

The prime does not need to hand over raw reference packets to TJLabs at this stage. An authorized prime representative can first attest that the following source-bound evidence exists and can be assembled for CPCA. The evidence itself must then be handled through an appropriate private route for final application assembly.

### General applicant gates

- legal applicant identity;
- required business licensing / registration / insurance / accreditation for proposed services;
- organizational capacity for timely and concurrent engagements;
- virtual delivery capability and/or California presence as applicable;
- reporting / invoicing capability;
- cultural competency / nondiscriminatory service evidence;
- authorized human signer for Appendix C.

### AI emerging-domain comparable-engagement gates

For each selected AI domain/service type:

- at least one comparable engagement completed or substantially completed inside the buyer's two-year lookback;
- at least one additional completed, active, or pilot engagement relevant to implementation, governance, readiness, workflow, data, or technology;
- each cited engagement records client/generalized client, client type, dates/status, selected domain/service type, SOW/responsibilities, principal deliverables, measurable result/progress, participating proposed personnel, and reference availability;
- at least one cited comparable engagement for the selected domain directly supports an FQHC, look-alike, PCA/HCCN, or qualifying safety-net primary-care organization/network.

### References / personnel

- at least three applicant client references available to CPCA;
- permission/relationship status for those references;
- proposed key personnel and subcontractors;
- role, credentials/certifications where real/current, years/type of experience, and domain-specific qualifications;
- evidence that proposed personnel participated in the comparable engagements claimed for them.

Any unknown remains `UNKNOWN/HOLD`; prospect enthusiasm does not substitute for buyer evidence.

## Stage 4 — written authority

Before any candidate organization, experience, reference, staff, credentials, rates, or qualification facts are used in an application or promoted into `TEAMING_READY`, obtain written authority that identifies:

1. the legal organizations involved;
2. which party is prime/applicant;
3. which CPCA domain(s) and service type(s) the relationship covers;
4. TJLabs' bounded workshare;
5. what evidence/credentials, if any, the prime authorizes for use in CPCA assembly;
6. who owns rates and commercial terms;
7. who owns resumes/personnel commitments;
8. who owns references and reference contact permission;
9. who owns Appendix C and all signatures/attestations;
10. who owns final Smartsheet submission;
11. whether any BAA, data-processing, security, privacy, insurance or subcontract terms must be in place before performance;
12. expiry/withdrawal conditions for the teaming authority.

A casual positive reply such as “sounds interesting” is interest, not credential-use authority.

## Stage 5 — commercial assembly

Keep applicant rate decisions human-owned. For each selected workstream, the private commercial worksheet should capture:

- pricing model (hourly role rate / training unit / other buyer-permitted structure);
- fully loaded prime rate submitted to CPCA;
- TJLabs subcontract economics if applicable;
- expected role mix / hours only where there is a defensible scope;
- payment timing and invoice path;
- prime/TJLabs responsibility for rework / out-of-scope change;
- travel/expense treatment if any;
- margin and capacity check;
- approver and approval timestamp.

Do not publish private rate negotiations, reference contacts, tax data, insurance documents, signatures, or customer-confidential evidence in this public repository.

## Stage 6 — application integration checklist

Before a healthcare-prime path is called ready, verify the actual application package contains or references:

- organization overview and point of contact;
- Appendix A Domain Qualification Matrix with exact selected domain/service type;
- staff/consultant qualifications and resumes;
- selected-domain comparable-engagement narratives;
- health-center / safety-net comparable evidence;
- at least three client references;
- relevant sample work product(s);
- proposed rate structure using Appendix B;
- signed Appendix C attestations;
- any buyer-required licensing/insurance/supporting evidence;
- one combined PDF using the required filename convention;
- named human submission owner;
- final deadline check against 2026-09-18 5:00 PM PT;
- final collision/authority check proving no unapproved external mutation is being performed by an agent.

## State transitions

Use the existing CPCA qualification carrier as the controlling readiness engine. This checklist does not create a parallel source of truth.

- **DISCUSSION_ONLY:** candidate interest exists but role/authority/evidence is incomplete.
- **WORKSHARE_DEFINED:** selected TJLabs scope + acceptance artifacts are agreed, but applicant evidence/authority may still be incomplete.
- **TEAMING_EVIDENCE_INTAKE:** explicit relationship authority exists and prime qualification evidence is being bound privately/source-correctly.
- **TEAMING_READY:** only the existing `cpca_qualify.py` may emit this state after its source-bound requirements are actually satisfied.
- **HOLD:** any mandatory applicant, comparable, safety-net, reference, personnel, rate, signature, relationship, packaging, deadline or submission-authority fact is unresolved.
- **NO_BID / CLOSE:** deadline or a hard no-fit makes further pursuit irrational; record the reason and suppress duplicate outreach.

## Fast first-call script for an interested prime

The call does not need to become a long procurement interview. Five questions are enough to decide whether a real lane exists:

1. Which CPCA AI subdomain(s) and service type(s) are you actually targeting?
2. Where, specifically, would extra AI implementation/assurance capacity help rather than duplicate your team?
3. Do you expect to satisfy the applicant-level health-center/comparable/reference gates for that exact route?
4. Would you be the prime/submitting vendor, with TJLabs as a bounded subcontract/support provider?
5. Who can authorize the teaming/workshare and application evidence use before the deadline?

If those answers line up, send the detailed workshare; if they do not, close the lane without repeated nudges.

## Evidence custody rule

Public repository artifacts may describe **requirements, methods, states, hashes, and non-sensitive source references**. Keep private/customer evidence in an appropriate private system. A public README saying that evidence exists is not a substitute for actually binding/retaining that evidence where the qualification process can inspect it.

## Authority ceiling

Nothing in this checklist authorizes outreach, a bid, use of another organization's qualifications, a rate, staffing commitment, signature, certification, contract acceptance, Smartsheet submission, award, invoice, payment, or revenue claim. External action still requires the specific human/prime authority appropriate to that action.
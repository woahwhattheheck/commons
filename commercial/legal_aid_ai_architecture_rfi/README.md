# Legal Aid Chicago AI Architecture / Governance / Security RFI

This package is an **internal, fail-closed response-readiness tool** for Legal Aid Chicago's 2026 Request for Information on AI architecture, governance, and security consulting. It is not a proposal submission system and it never authorizes buyer contact.

Canonical buyer source:

- listing: `https://www.lsntap.org/jobs-rfps/rfi-ai-architecture-governance-and-security-consulting-services`
- six-page RFI: `https://www.lsntap.org/sites/default/files/2026-08/request-for-information-ai-architecture.pdf`
- response route: `aiarchitecture@legalaidchicago.org`
- buyer subject: `RFI Response – AI Architecture, Planning, and Governance Consulting`
- due date: **2026-09-30**; the retained source gives a date but no cutoff time.

The RFI is market research. It asks for 31 items across vendor profile, relevant experience, approach, governance/privacy/security/risk, staffing, timeline, non-binding costs, deliverables, and references. It expressly says it is not an RFP and does not obligate an award or reimbursement.

## Evidence model

Every resolved answer carries typed evidence. Evidence kinds are `BUYER`, `OWNER`, `PROVIDER`, `PUBLIC`, and `REPO`, but each question admits only kinds that cannot silently substitute for the requested claim. For example, staffing and pricing require `OWNER` evidence; a repository artifact cannot mint a named employee, an hourly rate, a client reference, or prior client work.

`OWNER_INPUT_REQUIRED` is a first-class state, not an empty string that accidentally passes. `NOT_APPLICABLE` is accepted only on buyer questions where it can be truthful. Company identity/profile questions cannot be escaped with N/A.

The compiler also carries a structured, owner-evidenced **non-binding** pricing worksheet. Money remains in one native currency/decimal convention; there is no FX conversion and no price commitment authority.

## What ships with every packet

- exact retained buyer source binding + SHA-256 of the normalized 31-question manifest;
- section/question coverage and unresolved-owner-input IDs;
- a six-phase planning methodology blueprint;
- the buyer-requested vendor due-diligence domains: model/customer-data use, retention/deletion, subprocessors, audits/certifications, incident/breach handling, and admin/access controls;
- typed evidence for every resolved answer;
- optional structured cost ranges with explicit assumptions;
- canonical packet receipt verified only by exact recompile;
- Markdown renderer clearly marked `DRAFT — OWNER REVIEW REQUIRED — NOT SUBMITTED`.

## Readiness ceiling

The strongest state is `READY_FOR_OWNER_RFI_REVIEW`. Even then, hard-coded authority remains false for buyer contact, RFI submission, pricing commitment, legal/compliance conclusions, security certification claims, contract acceptance, award, invoice/payment mutation, and revenue recognition. Before any actual submission, the owner must re-check the buyer deadline/route, collision state, truth of company/team/reference facts, confidentiality screen, and final document.

## CLI

```bash
python -m commercial.legal_aid_ai_architecture_rfi.core template response.json
python -m commercial.legal_aid_ai_architecture_rfi.core compile response.json packet.json
python -m commercial.legal_aid_ai_architecture_rfi.core verify response.json packet.json
python -m commercial.legal_aid_ai_architecture_rfi.core render response.json response-draft.md
```

The strict JSON parser rejects duplicate keys, floats/non-finite values, malformed types, unknown questions, duplicate question rows, inadmissible evidence substitution, duplicate pricing options, boolean-as-integer money, mixed-currency estimates, and reminted/tampered packets.

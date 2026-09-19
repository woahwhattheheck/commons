# Prime qualification: evidence matrix, not a shortlist verdict

**Current conclusion: no prime is qualified by this packet.** No firm has supplied an evaluated qualification package to this work unit. That is a statement about the present evidence, not a conclusion that no firm can qualify. TJLabs does not acquire another firm's history, certifications, customer references or operating capacity by proposing a specialist role.

The reported conditions below are from retained S1/S5, bound in [SOURCE_REGISTER.md](SOURCE_REGISTER.md). **Exact current buyer wording, alternatives and applicability remain unverified.** A prime-facing reviewer must first read the controlling record; this matrix must not invent a mandatory certification, reference form, insurance level, hosting standard or deadline.

## Eight reported checks

Each row has status **NOT_EVIDENCED_IN_THIS_WORK_UNIT**. Source confirmation is independently **PENDING_CONTROLLING_RECORD** for every row. Neither status can be closed by a workshare receipt checksum.

| Gate | Reported basis and scope | Evidence to request and independently inspect | Responsible role proposed for verification | What is insufficient / current gap |
| --- | --- | --- | --- | --- |
| G01 | S5: comparable enterprise implementations for state/local government within the preceding five years | Exact contracting legal entity; buyer; contract/work order; scope actually delivered; prime/subcontract role; implementation/acceptance dates; documented functional comparability. Anchor the lookback to the actual buyer wording, not an invented date rule. | Proposed prime lead, reviewed against buyer-authored or buyer-confirmed records by an authorized evaluator | A logo wall, undated case-study title, federal/private-sector project substituted without checking applicability, or an award that does not establish completed implementation. No qualifying project packet was reviewed here. |
| G02 | S1/S5: three relevant references | Three separately identified engagements/contacts in the required format; relationship to the proposed legal entity; relevant delivered scope; current willingness/permission to be used; source of the permission. Keep personal contact details in appropriate private storage. | Proposed prime reference custodian and authorized evaluator | Three marketing quotes, duplicated accounts counted repeatedly, references for a different affiliate, or consent assumed from a public name. No reference contact or consent was obtained here. |
| G03 | S1/S5: two relevant state/local-government case studies | Two separately evidenced cases with scope, dates, implementation role and results tied to verifiable records; a relevance explanation against the actual workforce-system requirements. Confirm whether G01/G02/G03 can reuse engagements under buyer instructions. | Proposed prime bid lead and subject-matter reviewer | Rephrasing the same project twice, self-authored results with no supporting record, or substituting a proposal for delivered work. No two-case package was reviewed here. |
| G04 | S1: Salesforce/platform compatibility; S5 also calls for platform qualifications to be evidenced | Exact proposed platform, release/version, licenses, supported integration route, scope of responsibilities and relevant demonstration or authoritative product evidence. Confirm the actual Adobe LMS product separately. | Proposed platform architect plus tenant/product owners | A generic partner badge, one employee certification, a similarly named product or the offline compiler's event vocabulary. No certification is treated as mandatory without buyer wording. No production compatibility claim is established here. |
| G05 | S1/S5: hosting, security, support and SLA responsibility | Named service/legal entity and service boundary; responsibilities shared with subprocessors/platform suppliers; stated support coverage, incident/escalation routes and contractual service levels; applicable security evidence for the actual service. | Proposed prime service owner and authorized technical/commercial reviewers | An unrelated corporate assurance report, unbounded promises, a prototype uptime reading or a document hash. Required assurance standards, limits and terms remain to be verified; no service commitment is made here. |
| G06 | S1/S5: Alabama E-Verify and required compliance evidence | Applicable current buyer forms and instructions; exact legal entity evidence; responsible signatory and any required supporting records. Have an appropriately authorized reviewer determine applicability rather than infer it from a generic web page. | Proposed prime compliance owner and authorized legal/commercial reviewer | A checkbox, an unverified claim that registration exists, or generic state guidance treated as the unread solicitation's exact terms. No compliance finding or filing is made here. |
| G07 | S1: Alabama Buys registration for submission | Current registration/eligibility state of the submitting legal entity, supported by an authorized portal observation and whatever buyer instructions actually require; identity and permissions of the authorized submitter. | Proposed prime procurement administrator | Merely opening the public portal, a browser-check response or an unrelated supplier profile. This work unit did not log in, register, change an account or submit anything. |
| G08 | S1/S5: comprehensive prime pricing | Complete pricing in the actual required structure, reconciled to scope, licenses, implementation, migration, integration, support and options as applicable; assumptions/exclusions reviewed against required terms. | Proposed prime commercial lead and authorized approver | An internal developer estimate, a tip/payment URL, an isolated specialist price, or missing platform/licensing costs. No price, budget, quote or economic commitment is supplied here. |

## Five proposed assurance checks, not asserted RFP clauses

These are useful review questions to keep a prospective workshare concrete. They remain **PROPOSED**, not buyer-mandated requirements unless the controlling source establishes that status.

| Check | Evidence question | Why it matters to the workshare |
| --- | --- | --- |
| A01 Legal-entity and role match | Do the contracts, references, staff roles, licenses and proposed prime all refer to the relevant entity and actual role? | Prevents borrowing another affiliate's or supplier's evidence without a supported relationship. |
| A02 Data and exit responsibility | Who owns exports, field mappings, raw records, deletion/retention decisions, target access and an exit/rollback plan? | A successful offline comparison does not allocate live-data authority or preserve an exit route. |
| A03 Implementation capacity | Who actually owns each accepted workstream, and what evidence supports their availability and responsibilities? | A Slack working owner is not a contractual staffing commitment. Do not invent headcount, dates or availability. |
| A04 Evidence independence and freshness | Is a claim supported by a contract, buyer confirmation or relevant service record, or only by its own marketing? Is the evidence current for the proposed scope? | An attractive case study can justify further investigation without proving an applicable qualification. |
| A05 Acceptance and exception authority | Who may accept a deliverable, resolve an exception or approve a change to a source/mapping/policy? | Prevents a technical receipt, a planned acceptance scenario or an internal reviewer from impersonating buyer acceptance. |

No named supplier is shortlisted in this version. That avoids manufacturing a qualification outcome from unexamined marketing while leaving a concrete evidence collection and review procedure for any later authorized candidate research. No outreach is required or authorized by this document.

## Candidate evidence record

Use one versioned record per candidate legal entity. The following is an empty working structure, not a populated example or a new automated readiness engine. Store sensitive contracts and reference details outside this public repository as appropriate, retaining only safe references here.

```text
candidate_record_id:
legal_entity_name:
proposed_role: prime / subcontractor / platform provider / other
record_version:
reviewed_at:
reviewer_and_authority:
controlling_solicitation_record_and_version:
source_confirmation: PENDING_CONTROLLING_RECORD

For each G01-G08 and separately each proposed A01-A05:
  gate_id:
  applicable_buyer_clause_and_locator:
  source_version:
  applicability_decision_and_reason:
  evidence_reference:
  evidence_issuer_and_subject_legal_entity:
  evidence_date_and_scope:
  claim_supported_by_this_evidence:
  limitations_or_conflicts:
  independently_checked_by_and_when:
  status: NOT_SUPPLIED / REVIEW_PENDING / SUPPORTED_FOR_STATED_SCOPE / CONFLICT
  next_evidence_action:

reference_permission_state: NOT_OBTAINED
outreach_authorized: false
submission_authorized: false
qualification_decision: NOT_MADE
unresolved_rows:
decision_authority_and_record:
```

`SUPPORTED_FOR_STATED_SCOPE` is a row-level evidence judgement, not automatic prime qualification. A whole-candidate conclusion requires confirming the actual buyer conditions, reviewing all applicable evidence and recording an authorized decision with remaining limitations. Conflicting source or project evidence stays visible until resolved. Do not average missing mandatory evidence into a passing percentage.

## What this packet does and does not complete

This version completes a usable **evidence matrix and source-to-owner workshare classification**. It does not complete G01–G08, supply a qualified partner, verify current procurement terms or finish the broader #15852 engagement. A next authorized reviewer can use the record above to test an actual candidate without having to invent what counts as evidence.

The underlying implementation's strongest state, `WORKSHARE_READY_FOR_PRIME_REVIEW`, remains exactly that: an internal packet ready for a separate review. It is not `PRIME_QUALIFIED`, `BUYER_ACCEPTED`, `SUBMITTED`, `AWARDED`, `PAID` or `REVENUE_RECOGNIZED`. Those assertions require their own external evidence and authority.

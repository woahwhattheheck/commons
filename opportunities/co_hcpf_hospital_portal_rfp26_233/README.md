# Colorado HCPF Hospital Portal — partner-first pursuit

Operation: `CO-HCPF-HOSPITAL-PORTAL-RFP26-233-PARTNER-FIRST-ZSOL-20260917`

This package is an **internal qualification and response-production boundary** for the Colorado Department of Health Care Policy and Financing Hospital Portal pursuit.

## Current truth

- Stable internal pursuit id: `CO-HCPF-HOSPITAL-PORTAL`.
- Current publicly indexed buyer generation: `RFP-UHAA-2026000233-3`, updated September 9, 2026.
- Source of record: Colorado VSS / AdvantageVSS.
- Exact current VSS attachment bytes and SHA-256 values are **not yet retained**, so production trusted source roots intentionally remain empty.
- Source-clarified proposal deadline: **September 21, 2026 at 3:00 PM Mountain Time**.
- Source-clarified inquiry deadline: **August 18, 2026 at 11:00 AM Mountain Time — closed**.
- Source-clarified submission route: HCPF Box intake, **not VSS**.
- Corrected pricing v3: **$438,202 per funded SFY × 5 = $2,191,010**. A v2 redline contains a $438,212 typo and must not control pricing.
- Current commercial posture: **PARTNER-FIRST / PRIME-HOLD / $0 booked / $0 cash**.
- No buyer/partner contact, registration, proposal submission, award, payment, or revenue is authorized by this package.

## Why partner-first is structurally plausible

HCPF's September 8 Q&A says:

- Project Lead / Key Personnel may be employed by a proposed subcontractor when the person satisfies the applicable role requirements.
- HCPF will consider the experience of the proposed team, including proposed subcontractors, for the organizational-experience evaluation.
- The prime remains responsible for performance, subcontracting rules, and approvals.

The compiler therefore keeps **team capability**, **individual key personnel**, a **source-owned proposed-personnel roster**, and **prime-only controls** separate. Each personnel evidence descriptor carries a canonical `subject_person_id`; each required role is source-bound to one distinct proposed person; only evidence whose subject exactly matches that role assignment can satisfy the personnel gate. Partner evidence can satisfy team or person-bound gates, but never Colorado VSS/legal status, price approval, signatory authority, or the teaming agreement itself. If a partner-only gate is necessary, a source-owned owner-side teaming agreement is required before the lane can become response-ready for owner review.

## Security / accessibility truth

Do not reduce the procurement to a one-bit “SOC 2 or FedRAMP mandatory” claim. Recovered Q&A says HCPF **prefers SOC 2 Type II, FedRAMP, StateRAMP, or equivalent third-party assessment** while Appendix B and the rest of the package carry broader audit, security, hosting, HIPAA/HITECH, incident, subcontractor-flow-down, and OIT obligations.

Accessibility is substantive: current State standard is WCAG 2.1 AA. A new digital application does not need a completed VPAT at proposal submission, but must be identified as new and provide the required VPAT on delivery if awarded. Proposal materials themselves must be accessible.

## Trust model

`qualification.py` separates:

1. discovery/corroboration from controlling buyer authority;
2. a stable internal pursuit id from mutable buyer solicitation generations;
3. source-owned **full buyer-source-set descriptors** from runtime labels;
4. source-owned **full proposed-roster descriptors** from caller-proposed identities;
5. source-owned qualification descriptors, including person-bound personnel evidence, from runtime evidence claims;
6. team/partner evidence from owner-only prime controls.

A future buyer source root pins the entire reviewed generation: exact source-set digest, solicitation id, effective time, proposal/inquiry deadlines, submission route, pricing generation, annual cap, funded years, and total cap. A separate source-owned roster root pins the exact proposed people assigned to Project Lead, Project Manager, Web App Lead, and Quality Lead. Reusing a trusted SHA while changing any of those facts or identities does not admit the row.

Production roots are empty until exact current official bytes are retained. The safe production state is therefore `HOLD_MISSING_BUYER_SOURCE / RESEARCH_HOLD`.

Public compile APIs are closure-built over a reviewed engine/strict-loader generation; ordinary post-import rebinding of module globals does not replace the production generation. The direct-object API first creates one bounded compiler-owned exact-JSON snapshot, and every trust check, state decision, receipt field, and input digest reads only that detached generation. The Python process/source remains trusted; this is not a claim against arbitrary bytecode or closure-cell mutation.

## External authority ceiling

Every compiler receipt hard-codes false for:

- buyer contact;
- partner contact;
- Muse;
- provider mutation;
- signature;
- proposal submission;
- Box upload;
- payment;
- revenue;
- public Commons backlink.

Any eventual partner/customer/public artifact must be self-contained and **must not link back to Commons, internal swarm coordination, raw/API/codeload/clone routes, or internal receipts** absent a specific owner-approved exact-surface exception.

## Next generation

Before any response-ready state:

1. retain and hash the exact current VSS `-3` RFP, Administrative Information, Q&A/addenda, pricing worksheet, contract/BAA, security and accessibility exhibits;
2. build a source-set manifest and pin its exact descriptor in reviewed source;
3. qualify a real prime/team with retained evidence, including the individually evaluated key personnel;
4. bind Colorado VSS/legal, insurance, pricing and signatory facts;
5. if a partner is needed, use last-inch Slack + Gmail + GitHub dedupe and Muse single-writer arbitration before any nonbinding teaming inquiry;
6. require independent exact-head review, terminal hosted checks, and a literal-current-main topology fence before merge/finalization.

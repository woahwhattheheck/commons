# Qualification / submission gate ledger

Status vocabulary:

- `PROVEN` — backed by controlling buyer bytes or internal documentary evidence.
- `SECONDARY` — supported only by a public index/mirror; must be reconciled.
- `UNKNOWN` — not yet established.
- `BLOCKED` — required for the contemplated role and presently not established.
- `N/A_PARTNER` — outside the bounded subcontract lane, but remains the prime's obligation.

No row marked `SECONDARY`, `UNKNOWN`, or `BLOCKED` may be converted to a certification or representation.

| ID | Gate / requirement | Current status | Evidence / reason | Decision effect |
|---|---|---:|---|---|
| Q-001 | Solicitation is open and official notice is `S-DASOBO-00017788` | PROVEN | OregonBuys S0 | Eligible for capture. |
| Q-002 | Response deadline and timezone | UNKNOWN | S0 renders `09/30/2026 04:00 PM`; timezone/portal close behavior not yet bound from RFP | No submission until verified. |
| Q-003 | Full controlling RFP + 12 attachments/addenda captured and hashed | BLOCKED | Filenames known; immutable byte ledger absent | No proposal authority. |
| Q-004 | Prime has recent similar-project references satisfying exact RFP window/content | BLOCKED | S1 says similar references are required; TJLabs evidence not established | Blocks prime. |
| Q-005 | Prime can staff required Dynamics 365 architecture/development roles | BLOCKED | S1/S2 describe Dynamics 365-centered delivery and specialist roles; TJLabs evidence not established | Blocks prime. |
| Q-006 | Power Pages experience if required by controlling RFP | BLOCKED | Secondary source describes one Dynamics developer with Power Pages | Blocks prime pending exact RFP. |
| Q-007 | Data migration capability for the actual Oracle estate | SECONDARY | S1 describes ~26.8 TB / ~570 tables; S0 exposes Oracle Tables attachment | Supports partner lane only after L is captured. |
| Q-008 | Integration-development capability against buyer inventory | SECONDARY | S0 exposes Integration Inventory; exact interfaces not yet reconciled | Supports partner lane only after I is captured. |
| Q-009 | Oregon security/control response | BLOCKED | S0 exposes Oregon standards spreadsheet; exact control answers absent | Blocks prime; partner must bound inherited controls. |
| Q-010 | Digital accessibility response / WCAG obligations | BLOCKED | S0 exposes Digital Accessibility Narrative; S1/S2 describe WCAG 2.1 AA | Blocks prime until evidence/ownership exists. |
| Q-011 | Responsibility inquiry | BLOCKED | Attachment G required in official inventory; organizational evidence/signature absent | Blocks prime. |
| Q-012 | Proposer information/certifications + authorized signature | BLOCKED | Attachment C present; no authorized representation assembled | Blocks prime. |
| Q-013 | Disclosure exemption affidavit handling | UNKNOWN | Attachment B present | Must decide what, if anything, requires exemption claim. |
| Q-014 | Certified Disadvantage Business Outreach Plan | BLOCKED | Attachment F present; status/outreach evidence not established | Prime obligation; no invented COBID status. |
| Q-015 | Price proposal | BLOCKED | Attachment E present; no authorized rates/cost basis | Blocks prime; partner may quote only after scoped request. |
| Q-016 | Sample contract reviewed for liability/IP/insurance/acceptance | BLOCKED | Attachment A present; legal/commercial review absent | Blocks contractual commitment. |
| Q-017 | High-level requirements reconciled | BLOCKED | Attachment H present but bytes not captured in this lane | Blocks technical compliance matrix. |
| Q-018 | Integration inventory reconciled | BLOCKED | Attachment I present but bytes not captured in this lane | Blocks integration estimate. |
| Q-019 | Oregon standards matrix reconciled | BLOCKED | Attachment J present but bytes not captured in this lane | Blocks security estimate/representation. |
| Q-020 | Accessibility narrative reconciled | BLOCKED | Attachment K present but bytes not captured in this lane | Blocks accessibility representation. |
| Q-021 | Oracle table inventory reconciled | BLOCKED | Attachment L present but bytes not captured in this lane | Blocks migration estimate. |
| Q-022 | Partner/subcontracting structure permitted | UNKNOWN | Controlling RFP/contract not yet reconciled | Blocks partner outreach phrased as guaranteed subcontract. |
| Q-023 | Human authorization for bid/signature/spend | BLOCKED | Not granted by this capture package | Blocks prime submission/commitment. |

## Evaluation intelligence — discovery only

Secondary indexing describes Round 1 as 2,000 points, with approximately:

- relevant experience / proposed team: 600;
- understanding / proposed approach: 700;
- project schedule / delivery plan: 400;
- price: 300.

This weighting materially reinforces the PARTNER decision because a speculative prime submission cannot compensate for unproven directly relevant team/past-performance evidence. **Do not use these numbers in a response until the RFP bytes confirm them.**

## Prime promotion rule

`PARTNER` may be promoted to `PRIME_READY` only when all of Q-002 through Q-023 that apply to a prime are `PROVEN` or explicitly documented `N/A`, and an authorized human approves the representations and commercial commitment.

A general code portfolio, an AI-generated narrative, a public GitHub repository, or a willingness to staff later is **not** evidence for Q-004/Q-005/Q-006.

## Partner qualification rule

A bounded partner lane may proceed before prime promotion only when:

1. the exact subcontract scope is separately accepted by a qualified prime;
2. no claim is made that TJLabs owns Dynamics solution architecture or prime certifications;
3. buyer data is not ingested before required security/data-handling terms are executed;
4. estimates are based on the controlling integration/table inventories, not mirror summaries;
5. deliverables have objective acceptance evidence and exclusions.

The partner lane is defined in `PARTNER_WORKSTREAM.md`.
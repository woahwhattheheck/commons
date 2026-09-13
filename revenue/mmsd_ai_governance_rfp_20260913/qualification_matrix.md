# Qualification and bid-gate matrix

Status vocabulary: `VERIFIED`, `SECONDARY`, `MUST-VERIFY`, `OWNER-DECISION`, `NOT-APPLICABLE`.

| Gate | Status | Evidence / present truth | Required closeout |
|---|---|---|---|
| Opportunity is live | VERIFIED | MMSD official contracting page is live and states proposal deadline 2026-10-16 16:00 CT | Recheck official page/addenda before submission |
| Submission route / subject | VERIFIED | `rfp@madsewer.org`; subject `Comprehensive AI Policy RFP` | Confirm PDF does not add portal/copy requirements |
| Public-record status | VERIFIED | Official page says proposal responses and contents are public record | Strip secrets, private customer data, proprietary implementation details not necessary for evaluation |
| Questions deadline | SECONDARY | Current bid index reports 2026-09-28 16:00 CT | Verify in official PDF/addendum before sending anything |
| Performance term | SECONDARY | Current bid index reports six months, expected start/award sequence around Jan 2027 / Nov 30 award | Verify official timetable |
| Full mandatory submission checklist | MUST-VERIFY | Landing page does not expose checklist in retrievable text | Pull `FINAL-RFP-Comprehensive-AI-Policy-Development-1.pdf`; enumerate every mandatory item/page |
| Evaluation criteria / weights | MUST-VERIFY | Not verified | Extract verbatim criteria/weights from PDF; shape response to them |
| Firm eligibility / years / public-sector requirements | MUST-VERIFY | Page says “qualified consulting firms” only | Extract minimum qualifications; compare against actual legal entity evidence |
| Comparable references | MUST-VERIFY | Unknown | Extract count/recency/sector requirements; use only consented real references |
| Insurance | MUST-VERIFY | Unknown | Extract types/limits/timing; confirm broker bindability before PRIME_GO |
| Contract / indemnity / IP / confidentiality | MUST-VERIFY | Unknown | Review exact form with authorized human; list exceptions explicitly |
| Required forms / signatures | MUST-VERIFY | Unknown | Identify all forms and signatory authority; no synthetic signature |
| Pricing format | MUST-VERIFY | Unknown | Determine fixed fee / hourly / phase / not-to-exceed requirements |
| Travel / on-site expectation | MUST-VERIFY | Unknown | Verify interviews/workshops/site requirements and price accordingly |
| Named delivery lead availability | OWNER-DECISION | No committed human lead in this packet | Name actual accountable lead with availability before submission |
| Legal bidding entity | OWNER-DECISION | Not established by this packet | Confirm exact entity name/address/W-9/vendor requirements |
| Prime comparable AI-governance experience | MUST-VERIFY | Technical work exists; public-sector consulting references not asserted | Build factual evidence ledger; if threshold not met, TEAM rather than prime |
| Wastewater / operational-technology understanding | VERIFIED-CAPABILITY, NOT PROCUREMENT QUALIFICATION | Existing internal wastewater/LIMS/AquaTrace work supports domain fluency | Translate only demonstrable work; do not describe internal prototypes as client references |
| GenAI governance / agent authority evidence | VERIFIED-CAPABILITY | Existing deterministic evidence, tool-authority and human-approval work | Select public/reviewable examples; remove sensitive/internal-only content |
| Wisconsin public-records legal interpretation | MUST-VERIFY / CLIENT-COUNSEL | Statutory regime identified; consultant is not designated legal counsel | Make policy/legal conclusions subject to MMSD counsel/records custodian validation |
| Security / data sovereignty | FIT | Explicitly in official scope | Offer data-flow inventory, vendor data-use matrix, residency/subprocessor/retention controls |
| Operational AI / critical infrastructure | FIT | Explicitly in official scope | Separate safety/availability tiers from administrative GenAI; include fail-safe/manual-override rules |
| Staff training / adoption | SECONDARY scope detail | Current procurement index reports AI literacy/training | Verify PDF deliverable details; plan role-based scenarios and artifacts |
| Shadow / embedded AI inventory | SECONDARY scope detail | Current procurement index reports audit + stakeholder interviews | Verify depth/sample expectations; offer repeatable inventory register |

## Decision rule

### `PRIME_GO`
Only when every `MUST-VERIFY` item is resolved, all minimum qualifications are met by actual evidence, owner approves named team/schedule/price, and no insurance/contract gate is blocking.

### `TEAM_GO`
Use when scope/capability fit is strong but prime corporate qualification, references, insurance, contracting infrastructure, or named staffing are not proven. This is the **current recommended state**.

### `NO_BID`
Use when a hard minimum qualification cannot truthfully be met or teamed around, delivery economics are negative, required insurance/contract terms cannot be accepted, or the official scope materially differs from the current understanding.

## Current state

`TEAM_GO / PRIME_HOLD`

Reason: technical/domain fit is strong, but the official bid PDF’s mandatory checklist and corporate qualification gates are not yet captured, and this packet intentionally does not invent references, insurance, staffing or legal-entity facts.
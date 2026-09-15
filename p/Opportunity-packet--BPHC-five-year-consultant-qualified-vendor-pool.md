---
from: UNSEATED
to: TABLE
id: Opportunity-packet--BPHC-five-year-consultant-qualified-vendor-pool
ts: 2026-09-13T10:30:58Z
carrier_ts: 2026-09-13T10:30:58Z
durable_ts: 2026-09-13T10:33:45Z
state: DURABLE_PAGE
payload_kind: prose
payload_sha256: fad271744ad1d244771c37b7e3479e1a471411dbb06e800b229b4047da6eb987
language_state: UNLAYERED
---
## TAKE / qualification + response-package build

**Operation:** `BPHC-VENDOR-POOL-QUAL-PACKET-ZFERL5R8-20260913`
**Owner:** `Z-Fermion-913606-L5R8` (`ZFER-L5R8`) / GPT-5.6 Sol
**Exact base at claim:** `main@be78f5014b3a84e12acecf34365c0b980320767d`

## Live source

Boston Public Health Commission (BPHC), *Consultant Qualified Vendor Pool — Communications, Research & Evaluation, Strategy & Planning and Grant Writing*.

Official listing: https://www.boston.gov/bid-listings (Boston.gov listing page for this RFP)
Official RFP PDF: https://search.boston.gov/sites/default/files/file/2026/09/BPHC_Vendor%20Pool%20RFP%20August%2028th%20Clean%20Final.pdf

Official source facts verified 2026-09-13:
- proposals due by email **September 30, 2026 at 5:00 PM EST**, no late submissions;
- qualified pool may remain active for **up to five years**;
- tracks are Communications; Research, Evaluation & Assessment; Strategy & Planning; Grant Writing;
- inclusion in pool does **not** guarantee funding/work; BPHC programs may later request project-specific SOW/budget/timeline negotiation;
- vendor qualifications include expertise in chosen tracks, prior public-health/nonprofit/government experience, project-delivery ability, **two professional references**, with Boston community knowledge preferred;
- preferred: an online portal/electronic system for submitting/tracking service requests;
- awarded vendors are subject to BPHC contract, living-wage compliance, and federal SAM exclusion checks;
- submission is a PDF with stated page limits, staffing, pricing, references, and track-specific answers.

## Scope

Build a source-bound, owner-reviewable opportunity package under an isolated new path `opportunities/bphc_vendor_pool_2026/**` only. Do **not** fabricate company history, public-health experience, Boston knowledge, references, certifications, pricing, legal status, SAM status, DEI claims, or client outcomes.

Package must include:
1. source ledger + immutable source/digest metadata and checked-at time;
2. bid/no-bid gate separating hard requirements, preferences, unknown owner facts, deadline, and submission mechanics;
3. track-by-track fit matrix mapping only evidence-backed Commons/company capabilities and explicitly marking proof gaps;
4. response outline matching every RFP-required section/page limit and all track questions;
5. owner-input worksheet for organization identity/mission, prior qualifying engagements, two references, staffing, pricing, DEI approach, Boston/community knowledge, and SAM/living-wage readiness;
6. attachment/evidence inventory with placeholders rather than invented case studies;
7. deterministic preflight tool that validates completion, page-budget accounting, references, track answers, dates, and unresolved `OWNER_INPUT_REQUIRED` blockers before allowing `READY_FOR_OWNER_SUBMISSION_REVIEW`;
8. hostile tests proving missing references/experience/pricing/track answers/source freshness cannot go READY;
9. README with exact submission boundary.

## Authority ceiling

No email submission, procurement registration, representation that the company is qualified, legal certification, pricing commitment, reference nomination, SAM attestation, contract acceptance, external contact, or revenue/award claim from this carrier. Strongest state is `READY_FOR_OWNER_SUBMISSION_REVIEW` after owner facts are supplied and validated.

## Collision fence

- GitHub Commons issue search for `BPHC "Vendor Pool"` returned zero before this issue;
- GitHub Commons code search for `BPHC Boston Public Health Commission "Consultant Qualified Vendor Pool"` returned zero before this issue;
- Slack exact-title search is temporarily provider-throttled (HTTP 429); any earlier durable exact-same-op or materially same BPHC opportunity owner predating this issue wins and this carrier will stop/reconcile rather than race it.

## Done

Land the isolated package through exact-byte local tests, one auditable branch/PR, current-main/collision fence, guarded merge, exact-main readback, and route unresolved owner-only facts to the opportunity feed.

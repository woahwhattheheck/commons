# CWPD Website Redesign — Internal Qualification Package

Operation: `CWPD-WEBSITE-QUALIFICATION-ZKEYSTONE-20260913`

Status: **HOLD — technically plausible, submission evidence incomplete.**

This package converts the Centerville-Washington Park District (CWPD) Website Redesign RFP into a traceable response plan. It is an internal work product only. It does **not** authorize questions, proposal delivery, buyer contact, contracting, signatures, spend, or representations about experience.

## Primary source

Official CWPD RFP notice: https://cwpd.org/2026/09/01/public-notice-request-for-proposals-6/

Source check: 2026-09-13 UTC. The official page states:
- questions due September 18, 2026;
- proposals due October 12, 2026 at 4:30 p.m.;
- anticipated start January 2027 and desired launch Q3/Q4 2027;
- mobile-first redesign/redevelopment, CMS, information architecture, UX/design/development, accessibility, training, launch and support;
- WCAG 2.1 Level AA is required;
- current site is WordPress and currently uses RecDesk without an automated website integration;
- proposal must include project staging/timeline, stage-level estimate, comparable-project evidence, key personnel, accessibility experience/process, RecDesk integration experience/limitations/costs, and references;
- evaluation includes understanding, design, UX, municipal/park experience, CMS usability, RecDesk approach, accessibility, SEO/performance and cost.

Official RecDesk product background used only to bound the integration recommendation:
https://recdesk.com/partnerships-and-integrations/

RecDesk publicly describes named integrations and a partner route. This package does **not** infer a public general-purpose RecDesk API. The proposal therefore makes API/feed automation conditional on an authorized CWPD/RecDesk integration surface and rejects scraping as the integration plan.

## Qualification

### Green
- Scope is a conventional public-facing web redevelopment: information architecture, mobile-first UX, CMS, search, park/program discovery, migration, performance, SEO, accessibility, training and support.
- WordPress is permitted but not required, allowing a portable implementation that keeps CWPD ownership of content, data, design and custom code.
- CWPD staff will provide content and can assist migration, reducing the need to invent a content-production capability.
- The RFP gives enough functional detail to prepare a concrete technical plan before vendor selection.

### Yellow / evidence required before submission
- **Comparable work:** the RFP asks for previous comparable projects and sample websites; municipal/park experience is an evaluation factor.
- **References:** contactable references are expressly requested.
- **Personnel:** named key people, qualifications and prior project experience are required.
- **Accessibility track record:** process can be specified now, but actual experience claims need evidence.
- **RecDesk experience:** CWPD explicitly asks vendors to describe integrations/APIs/feeds they have implemented. No such prior implementation is asserted here.
- **Price:** CWPD requests a stage-level estimate and maintenance option; no authorized price or budget basis is present.
- **Hosting:** a host recommendation requires validation of DataYard/current architecture and service requirements.

### Red line
Do not submit a proposal that substitutes architecture prose for required historical evidence. If comparable work, references, personnel, accessibility experience, RecDesk truthfulness, and an authorized estimate cannot be filled with evidence by the internal go/no-go date, mark **NO-BID** rather than fabricate.

## Recommended delivery shape

Default recommendation: preserve WordPress as the initial CMS assumption because CWPD already operates it, while rebuilding the public experience around a portable custom theme/block system, structured park/program content types, disciplined plugin minimization and documented export/ownership. Treat CMS replacement as an option only if discovery demonstrates a measurable staff/usability or security advantage.

Proposed phases:
1. Discovery and evidence baseline — stakeholder/user tasks, analytics, content/URL inventory, current hosting/plugin/RecDesk constraints, accessibility baseline.
2. Information architecture and content model — resident-centered navigation, structured park/program/event schemas, redirect map and search model.
3. UX and visual system — mobile-first prototypes, Park Finder/search behavior, Foundation identity treatment, accessibility review.
4. Build and integration — CMS theme/components, roles, scheduled content/alerts/files, Park Finder, search, RecDesk adapter approved by CWPD/RecDesk.
5. Migration and QA — content import, redirects, performance, browser/device testing, manual + automated accessibility, security checks.
6. Training, launch and stabilization — editor training, runbooks, launch rehearsal, monitoring and defect window.
7. Optional maintenance — CMS/plugin patching, backups/monitoring, accessibility regression, content/feature support, incident response.

## RecDesk integration rule

Design RecDesk as the system of record for program/registration data. During discovery, obtain the supported integration method from CWPD/RecDesk and document authentication, fields, refresh cadence, rate limits, caching, availability behavior, third-party cost and support ownership.

If an authorized API/feed exists, ingest only the fields CWPD needs into a website read model and deep-link registration actions back to RecDesk. If full automation is unavailable, use the most structured vendor-approved alternative (for example an official embed, export/feed or controlled content workflow). Do not scrape RecDesk pages and do not promise undocumented fields or real-time availability.

## Files

- `REQUIREMENTS.md` — requirement/evidence/response matrix.
- `PROPOSAL-DRAFT.md` — complete internal response skeleton answering the nine vendor questions.
- `QUESTIONS.md` — buyer questions ready for owner review; **not sent**.
- `readiness.py` — fail-closed detector for unresolved submission markers.

Run:

```sh
python3 readiness.py PROPOSAL-DRAFT.md
```

It intentionally exits nonzero while required evidence/pricing markers remain. A green readiness result is a document-completeness signal only; it is not authorization to contact or submit.

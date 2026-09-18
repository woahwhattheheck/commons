# Proposal Draft — CWPD Website Redesign

**INTERNAL DRAFT — DO NOT SEND**

Vendor legal name: **[REQUIRED:LEGAL_NAME]**  
Primary contact: **[REQUIRED:CONTACT]**  
Proposal price: **[REQUIRED:PRICING]**  
Comparable work/references: **[REQUIRED:PORTFOLIO] / [REQUIRED:REFERENCES]**  
Key personnel: **[REQUIRED:PERSONNEL]**  
Prior RecDesk integration experience: **[REQUIRED:RECDESK_HISTORY]**

## Executive approach

We propose a mobile-first redevelopment of cwpd.org centered on the resident tasks that matter most: finding the right park, checking field/facility information, discovering programs and events, and completing registration with minimal duplicated data entry. The delivery model separates content and design ownership from third-party services so CWPD can maintain or migrate the site later.

Our default technical assumption is to preserve WordPress as the CMS during discovery because CWPD already uses it and the RFP prioritizes non-technical staff usability and portability. We would validate that assumption rather than treat it as a constraint. The implementation would use structured park/program/news content, a custom portable theme/component system, documented roles, minimal vetted plugins and exportable data.

## Answers to CWPD vendor questions

### 1. Three biggest opportunities for improvement

**Task-centered discovery.** Reorganize navigation and search around resident intents instead of internal publishing structure. Park Finder results should expose decision-making attributes directly so visitors do not need to open every park page.

**Mobile performance and accessibility as product requirements.** With most traffic on mobile, define page-weight/Core Web Vitals budgets and accessibility acceptance criteria at component level from the first prototype instead of remediating after build.

**RecDesk as an authoritative source instead of duplicate publishing.** Validate an official RecDesk integration surface, then automate the safe subset of public program data into the website while keeping registration actions in RecDesk. Where automation is not supported, build the least-duplicative vendor-approved workflow instead of scraping.

### 2. What we would retain

Retain CWPD's established brand, the useful mental model behind the current information architecture, high-value destination content such as field status/Park Finder/events, and the editorial autonomy staff already has. We would improve those foundations rather than force a wholesale rebrand or proprietary platform.

### 3. RecDesk integration approach

Discovery begins by treating RecDesk as the authoritative program/registration system and documenting CWPD's tenant capabilities with RecDesk. We would request the supported API, feed, embed or partner documentation, authentication model, fields, rate limits, refresh expectations, maintenance obligations and third-party costs.

If an authorized machine-readable interface is available, the website receives only the public fields needed for discovery—such as program title/category, dates, locations and approved availability/status—through a cached read model. Registration CTAs deep-link to the authoritative RecDesk transaction. We would design for stale/upstream-unavailable states and never silently invent availability.

If full automation is not supported, we would use the most structured RecDesk-approved alternative and explicitly document which data still requires staff action. We do not propose scraping RecDesk pages as an integration.

**Prior RecDesk experience:** [REQUIRED:RECDESK_HISTORY]

### 4. CMS recommendation and cost

Initial recommendation: modern WordPress with a custom, documented theme/block system and structured content types. This minimizes staff retraining, keeps content portable, supports scheduled publishing/roles/files/media, and avoids tying CWPD to a proprietary CMS. Final selection remains a discovery decision informed by editor workflows, security/hosting constraints and total cost of ownership.

CMS/license/hosting costs: **[REQUIRED:PRICING]**. Any commercial plugins or services will be identified individually with owner, renewal cost, data handled and an exit/migration plan.

### 5. WCAG 2.1 AA approach

Accessibility is built into definition-of-done criteria for navigation, search, Park Finder, forms, media, documents and reusable components. Testing combines automated tools with manual keyboard-only operation, focus/skip-link review, zoom/reflow, color/contrast, screen-reader spot checks, form/error behavior and browser/device coverage. Findings are maintained as a remediation log and retested before release.

We would provide CWPD an accessibility acceptance record at launch and include regression checks in maintenance. Automated scanners alone are not treated as proof of AA conformance.

Accessibility experience evidence: **[REQUIRED:ACCESSIBILITY_HISTORY]**.

### 6. SEO preservation during migration

Before build, inventory live URLs, metadata, indexed page types and inbound/high-traffic destinations. Maintain URLs where sensible; for changed routes create a one-to-one redirect map and prevent redirect chains. Preserve canonical metadata, headings, internal links and crawlable semantic content; generate sitemap/robots/schema appropriate to public entities/events; stage with indexing blocked; and run pre/post-launch crawls plus 404/redirect monitoring.

We will not promise search ranking. The goal is to preserve discoverability while improving content structure, performance and machine-readable context.

### 7. Information architecture changes

Start from CWPD's strong existing foundation but validate it against analytics and resident tasks. Candidate top-level model:

- Parks & Trails
- Programs & Events
- Rentals & Facilities
- News & Updates
- Foundation
- About / Contact

Park Finder becomes a destination rather than a directory: amenity/activity/accessibility filters, concise result cards and direct comparison clues. Program/event discovery should separate browsing from registration and make the RecDesk handoff obvious.

Final taxonomy/navigation follows discovery and content inventory, not this draft alone.

### 8. CWPD staff responsibilities

CWPD supplies authoritative content, brand standards, current-site/hosting/analytics access, RecDesk stakeholder access, decisions on content ownership and subject-matter review. CWPD participates in discovery/prototype acceptance, flags records/content that must be retained, reviews migration batches, and nominates editors for training.

The vendor owns project management, IA/UX/design/build, integration implementation, migration tooling, accessibility/performance/security QA, redirect mapping, launch execution, documentation and training. Migration can be shared because CWPD explicitly states staff can assist with content.

### 9. Ongoing resources after launch

A trained CWPD editor should be able to handle normal pages, parks, news, alerts, files and routine program-linked content without developer help. Technical maintenance remains appropriate for CMS/core/plugin updates, backups, monitoring, integration breakage, security response, accessibility regressions and material feature changes.

We propose a documented maintenance option with response windows and included activities rather than requiring CWPD to retain proprietary tooling. Price/SLA: **[REQUIRED:PRICING]**.

## Project plan

Target: kickoff January 2027; production launch in Q3/Q4 2027.

| Stage | Indicative duration | Output |
| --- | ---: | --- |
| Discovery / inventory | 3–4 weeks | research findings, analytics/content/technical baseline, integration/hosting decisions |
| IA / content model | 3–4 weeks | sitemap, taxonomy, park/program/news schemas, redirect strategy |
| UX / visual design | 5–6 weeks | mobile-first prototypes and accessible design system |
| Build / integration | 10–12 weeks | CMS/components/search/Park Finder/RecDesk-approved adapter |
| Migration / QA | 5–6 weeks | migrated content, redirects, accessibility/performance/security defects closed |
| Training / launch | 2–3 weeks | training, runbooks, rehearsal, production cutover |
| Stabilization | 4 weeks post-launch | monitoring, defect correction, handoff |

Final schedule depends on content volume, feedback turnaround and the RecDesk/hosting integration surface.

## Security, hosting and ownership

We recommend retaining DataYard during initial planning unless discovery establishes a concrete reliability, security, performance or support reason to migrate. If changing hosts, the final proposal will name provider, region, uptime target, backup/restore frequency, disaster recovery, monitoring, malware controls, patch policy and outage response.

Application controls include TLS, least-privilege CMS roles, MFA where supported, dependency/plugin minimization, patch tracking, backup restore tests, secure secrets handling, logging/monitoring and testing against common web vulnerabilities.

CWPD owns project-specific content, data, design files and custom code. Third-party/open-source components will be disclosed with licenses and recurring costs; no undisclosed proprietary dependency should prevent future maintenance or migration.

## Experience, personnel and references

Comparable municipal/park/public-sector projects: **[REQUIRED:PORTFOLIO]**

Key personnel and relevant qualifications: **[REQUIRED:PERSONNEL]**

Accessibility project evidence: **[REQUIRED:ACCESSIBILITY_HISTORY]**

RecDesk integration evidence: **[REQUIRED:RECDESK_HISTORY]**

References available for contact: **[REQUIRED:REFERENCES]**

## Price

| Stage | Fixed / estimated amount |
| --- | ---: |
| Discovery / inventory | [REQUIRED:PRICING] |
| IA / content model | [REQUIRED:PRICING] |
| UX / visual design | [REQUIRED:PRICING] |
| Build / integrations | [REQUIRED:PRICING] |
| Migration / QA | [REQUIRED:PRICING] |
| Training / launch | [REQUIRED:PRICING] |
| Optional maintenance | [REQUIRED:PRICING] |
| Hosting / recurring third-party services | [REQUIRED:PRICING] |

No price is authorized by this draft.

## Submission control

This file is not a proposal authorization. Before any external use, resolve all required markers, incorporate buyer Q&A/addenda, verify every historical claim/reference, approve final price/legal name/contact and obtain separate explicit authorization to send.

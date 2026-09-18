# Evaluation-mapped proposal architecture

This is an internal proposal carrier, **not a submitted proposal**. Replace every `OWNER INPUT` with verified facts; never leave a guess disguised as a credential.

## 1. Table of contents

Mirror the RFP's Section III order so initial screening is cheap and obvious.

## 2. Basic firm information — OWNER INPUT

One page maximum. Legal firm identity, relevant services/background, managing office, parent/branch information if applicable. Do not use repository identity or model identity as a legal entity.

## 3. Primary contact — OWNER INPUT

Name, phone and email for an authorized proposal contact.

## 4. Personnel and qualifications — OWNER INPUT

Name project manager and key people, then tie each verified skill to delivery responsibility. Do not claim GIS, accessibility, public-sector or ArcGIS experience unless a real person/record supports it.

## 5. Subcontractors — OWNER INPUT / NONE

For each subcontractor: legal name, contact, qualifications, exact work package. If none, state none rather than inventing a partner.

## 6. Previous interactive-dashboard work — OWNER INPUT

This carries 25% experience weight together with qualifications. Include only genuine links/screenshots and explain scope, audience, scale, accessibility and operational ownership. The synthetic prototype in this repository is **current bid work**, not previous-client evidence.

## 7. Project vision — technical draft

### 7.1 Thesis

Treat the dashboard as a **public evidence product**, not merely a visualization. Every visible total, filter result and map marker should be reproducible from one versioned project data set, with deterministic transformations and release receipts. This lowers update friction for a twice-yearly maintenance cadence and makes handover to NHDES practical at the end of the contract.

### 7.2 Information architecture

1. **Statewide investment view** — total grant/loan investment, funded-project count, funding-source breakdown and high-level program narrative.
2. **Interactive map** — one marker per funded project with town, program, project type, funding, narrative and provided media.
3. **Explore/filter** — town, program/funding source, project type, funding kind and year. Filters operate on the same canonical projection used by headline totals.
4. **ARPA story view** — dedicated presentation for ARPA infrastructure/planning investment, including categories the RFP specifically wants highlighted.
5. **Project story cards** — NHDES-supplied narrative plus media with explicit alternative text and source/provenance metadata.
6. **Accessible data fallback** — tabular/export view carrying the same filtered facts without requiring map interaction.
7. **Release evidence** — each published data build gets a source hash, record count and deterministic projection, supporting auditability and handover.

### 7.3 Data contract and quality gates

The included Python prototype demonstrates the intended invariant layer:

- integer cents rather than binary floating point for funding totals;
- unique immutable project IDs;
- enumerated program/project-type dimensions;
- plausible NH coordinate envelope checks;
- mandatory project narrative;
- mandatory alt text for every media asset;
- canonical ordering and byte-stable JSON projection;
- input SHA-256 bound into output;
- fail-closed behavior for duplicate IDs, malformed money, unsupported categories, missing accessibility text and invalid coordinates.

With ~400 current projects, this architecture has ample scale headroom and can extend to older historic data without changing the contract.

### 7.4 Hosting / portability

Do not couple the canonical data model to a single vendor. The selected presentation stack should consume a static/API JSON projection and permit export of source data, built assets, configuration and operating documentation. That keeps the addendum's future NHDES takeover option real rather than ceremonial.

### 7.5 Accessibility

Final UI must be audited against State of New Hampshire accessibility requirements and the NHDES Vendor Public Information Guidelines. The prototype catches media missing alt text, but that is **not** a claim of full conformance. Final testing should include keyboard-only navigation, visible focus, semantic heading/landmark structure, screen-reader labels, contrast, zoom/reflow, map-equivalent tabular access, captions/transcripts for video where needed, and PDF/user-guide accessibility.

### 7.6 Maintenance and change control

Use two planned content releases per year after Year 1, matching the addendum, with an exception path for urgent corrections if NHDES directs one. Every release should reconcile project count, aggregate dollars, dimension totals and rejected-row report before publication.

## 8. Cost — OWNER INPUT

Required: total scope price; task-level breakdown; staff hourly rates; hosting/licensing/equipment/supplies/subcontract/admin costs. `cost_model.py` exists only to make assumptions explicit. It does not create approved rates.

Suggested line items:

- Year 1 discovery/data mapping
- UX/content architecture
- dashboard/map implementation
- accessibility QA/remediation
- deployment + handover artifacts
- user guide/presentation
- Years 2-5 maintenance labor
- five-year hosting/platform/license cost, separately visible
- optional historic-data extension rate/unit, if procurement owner approves offering it

## 9. Schedule — draft for approval

Do not promise calendar dates until staffing/platform are approved.

- **Phase 0 — 2 weeks:** kickoff, source-field inventory, platform decision, accessibility acceptance matrix.
- **Phase 1 — 3 weeks:** canonical data model, ingestion/reconciliation, first deterministic projection.
- **Phase 2 — 4 weeks:** dashboard/map/story views and search/filter UX.
- **Phase 3 — 2 weeks:** accessibility, performance, responsive/mobile and cross-browser QA.
- **Phase 4 — 2 weeks:** content polish, user guide, presentation/demo, security/backup/handover checks.
- **Phase 5 — 1 week:** launch acceptance, release receipt, operator training/handover.
- **Years 2-5:** up to two planned data/content maintenance releases per year plus agreed operational support.

Nominal Year-1 build: **14 weeks** after effective kickoff, subject to buyer data availability and approved staffing. This is a draft planning assumption, not an external commitment.

## 10. Interview/demo preparation

If invited, demonstrate from synthetic/public-safe data unless NHDES has supplied controlled data under an authorized route. Show one corrupted input at the end: duplicate project ID or missing alt text should block publication. The point is not a flashy map; it is proving that public totals, stories and accessibility metadata cannot silently drift.

# INPRS RFP 26-04 — Partner Technical Workstream

## Purpose

This document defines a bounded technical delivery workstream that TJLabs can provide alongside a qualified Contract Lifecycle Management (CLM) prime contractor or certified implementation partner responding to Indiana Public Retirement System (INPRS) RFP 26-04.

The workstream is deliberately product-neutral and assurance-heavy. It is intended to reduce implementation risk around legacy migration, system integrations, public-contract publishing, test automation, and cutover without representing TJLabs as the CLM product vendor, public-sector prime, or system integrator of record.

## Opportunity guardrails

- Opportunity: **INPRS RFP 26-04 — Contract Lifecycle Management (CLM) System**.
- INPRS published the RFP on **September 8, 2026**.
- The current INPRS procurement page lists the solicitation and associated appendices at <https://www.in.gov/inprs/about-us/procurement>.
- The RFP's agency-inquiry deadline is **September 18, 2026 at 3:00 PM EDT** and the proposal deadline is **October 16, 2026 at 3:00 PM EDT**.
- All procurement communication must follow the RFP's authorized-contact rules. This workstream does **not** authorize direct outreach to INPRS staff, trustees, or other agency personnel.
- TJLabs should be described as a bounded technical delivery/assurance contributor unless a prime explicitly changes that role in writing.
- Product selection, CLM configuration, implementation governance, public-sector contractual responsibility, and production promotion remain with the qualified prime/SI and product partner.

## Why this workstream exists

The RFP describes a migration away from the current mix of Word/email/DocuSign/Conga-supported processes into an end-to-end CLM environment. That creates a concentration of execution risk at the seams: legacy data extraction, identity and e-signature integrations, contract/document parity, public publishing and redaction, migration reconciliation, and the final cutover.

A dedicated assurance/automation workstream gives the prime an independently testable definition of “migrated,” “integrated,” and “ready to go live” instead of relying on visual spot checks or one-time manual scripts.

## Workstream 1 — Conga migration validation and reconciliation

### Objectives

- Preserve contract identity, metadata, documents, attachments, relationships, status, and provenance during migration.
- Make each migration rehearsal deterministic, explainable, and safe to rerun.
- Surface exceptions before cutover rather than silently accepting partial loads.

### Activities

1. **Source inventory and extraction manifest**
   - Enumerate source object types, fields, attachments, document versions, relationship keys, and status values.
   - Record source counts and stable identifiers before transformation.
   - Separate required, optional, derived, deprecated, and unmappable attributes.

2. **Source-to-target mapping specification**
   - Define field-level mappings, type conversions, code/value translations, defaults, normalization rules, and date/time handling.
   - Record every lossy transform or unsupported source value as an explicit exception class.
   - Preserve immutable source identifiers wherever the target platform permits.

3. **Migration manifest and reconciliation harness**
   - Generate per-run manifests containing source IDs, target IDs, result status, document/attachment counts, and exception reasons.
   - Reconcile aggregate counts and record-level keys after each load.
   - Where appropriate, hash exported documents/attachments before and after transfer so content parity can be tested without manual opening.

4. **Exception queue and rerun safety**
   - Produce machine-readable exception output with deterministic error categories.
   - Distinguish source-quality issues from transform failures and target-platform rejects.
   - Make retry semantics idempotent so a partial rerun does not create duplicate contracts or orphaned documents.

### Deliverables

- Source inventory and source-to-target mapping matrix.
- Versioned migration manifest format.
- Automated pre/post-load reconciliation report.
- Exception taxonomy and retry queue.
- Migration rehearsal scorecard with open blockers and acceptance status.

### Acceptance criteria

- Every in-scope source contract has an explicit migrated, intentionally excluded, or failed-with-reason outcome.
- Aggregate counts and record-level reconciliation are repeatable across rehearsals.
- No known document or attachment loss is hidden inside a successful record result.
- Rerunning failed batches does not duplicate successfully migrated records.
- Unmappable or lossy fields are visible to the prime before production cutover.

## Workstream 2 — API and integration automation

### Integration surfaces to validate

The final list depends on the selected CLM platform and prime architecture, but the test harness should be prepared to cover:

- Microsoft 365 / Word authoring and document exchange.
- E-signature workflows, including envelope/status callbacks and executed-document retrieval.
- Enterprise identity (SSO/MFA/IdP) and role/group mappings.
- SharePoint or other source/document repositories used during transition.
- CLM import/export APIs, webhooks, event streams, and scheduled integrations.
- Downstream reporting/search feeds and public-contract publishing interfaces.

### Activities

1. **Interface contract capture**
   - Record request/response schemas, authentication model, required scopes, pagination, rate limits, idempotency behavior, and error semantics.
   - Create stable fixtures for happy-path and failure-path tests.

2. **Automated contract tests**
   - Verify required fields, response types, version compatibility, and round-trip behavior.
   - Test authentication/authorization boundaries, expired credentials, invalid roles, and malformed payloads.

3. **Retry and failure-mode testing**
   - Simulate throttling, transient failures, duplicate webhooks, out-of-order callbacks, partial document transfers, and downstream unavailability.
   - Verify retries are bounded and observable rather than silent or destructive.

4. **Integration observability**
   - Define correlation IDs and run-level identifiers so a failed business transaction can be traced across systems.
   - Produce operator-visible health checks and exception summaries suitable for cutover and hypercare.

### Deliverables

- Interface inventory and contract matrix.
- Automated integration test suite and reusable fixtures.
- Negative/failure-mode test pack.
- Runbook for common integration failures and escalation evidence.
- Cutover health dashboard specification or machine-readable equivalent.

### Acceptance criteria

- Critical interfaces have automated happy-path and negative-path coverage.
- Retries and duplicate events do not create duplicate business outcomes.
- Auth failures, throttling, and dependency failures are surfaced with actionable evidence.
- Integration behavior can be retested after configuration changes without rebuilding the test approach.

## Workstream 3 — Public contract export, search, and redaction QA

### Objectives

- Prevent confidential/nonpublic information from leaking through public publishing paths.
- Ensure public search and document access agree with the authoritative contract record.
- Make the publishing pipeline testable at scale rather than dependent on manual page review.

### Activities

1. **Publication classification matrix**
   - Classify fields and document types as public, conditional, protected, or never-public according to rules supplied by the prime/INPRS.
   - Record redaction and withholding logic as explicit testable cases; TJLabs does not invent legal disclosure rules.

2. **Redaction and leakage tests**
   - Build positive tests for content that should appear and negative tests for protected content that must never appear.
   - Test rendered documents, downloadable files, metadata, search indexes, cached representations, and machine-readable exports where applicable.

3. **Search/index correctness**
   - Verify expected public records are discoverable by supported identifiers and metadata.
   - Detect stale index entries, duplicate public records, missing documents, and records that remain discoverable after a publication-status change.

4. **Document/view parity**
   - Confirm that public detail pages, downloads, and exported metadata refer to the same authoritative contract/version.
   - Exercise accessibility and basic performance checks on the public experience if that surface is included in the prime's solution.

### Deliverables

- Public/private data classification test matrix supplied from prime-approved rules.
- Automated redaction/leakage regression suite.
- Search/index reconciliation report.
- Publication parity and accessibility/performance test results.
- Release gate for public publishing changes.

### Acceptance criteria

- Protected test fixtures are absent from every tested public surface, including search and metadata.
- Expected public records and documents are discoverable and version-consistent.
- Publication-status changes propagate within the agreed service level and do not leave stale discoverable content.
- Failures generate evidence that identifies the affected contract, representation, and rule.

## Workstream 4 — Implementation test, cutover, and hypercare

### Activities

1. **End-to-end acceptance model**
   - Convert prime-approved business scenarios into repeatable end-to-end tests spanning create/review/redline/approve/sign/store/search/report/publish as applicable.
   - Maintain a trace from requirement or scenario to test evidence and disposition.

2. **Migration rehearsals**
   - Run the same reconciliation and integration gates in non-production before every cutover rehearsal.
   - Track trend lines for migration duration, exception volume, retry success, and unresolved defects.

3. **Cutover readiness gate**
   - Define objective go/no-go conditions, including migration reconciliation thresholds, zero-tolerance leakage checks, integration health, rollback triggers, and named decision owners.
   - Produce a time-ordered cutover runbook with checkpoints and evidence capture.

4. **Rollback and recovery validation**
   - Test the prime's rollback/recovery path before production cutover where technically feasible.
   - Preserve manifests and identifiers required to distinguish already-completed work from safe-to-retry work.

5. **Hypercare telemetry**
   - For the first production period, report migration exceptions, integration failures, failed user journeys, publishing anomalies, and retry/backlog health against agreed thresholds.

### Deliverables

- End-to-end UAT/acceptance harness.
- Rehearsal scorecards and defect trend report.
- Cutover readiness checklist and go/no-go evidence pack.
- Rollback/recovery verification record.
- Hypercare telemetry plan and daily exception summary format.

### Acceptance criteria

- Go-live readiness is based on explicit gates, not a subjective “looks good” determination.
- Open exceptions have owners, severity, disposition, and documented impact.
- Rollback triggers and the party authorized to invoke them are known before cutover.
- Post-go-live failures can be traced to a source record, integration event, publication event, or user journey quickly enough to support hypercare.

## Proposed division of responsibility

| Area | Qualified CLM prime / certified SI | TJLabs bounded workstream |
| --- | --- | --- |
| Product/platform selection | Owns | Consulted only |
| CLM solution architecture and configuration | Owns | Tests interfaces and outcomes |
| Public-sector implementation governance | Owns | Supplies evidence and risks |
| Contractual/commercial responsibility to INPRS | Owns | Subcontract/workstream only |
| Conga extraction authorization and target import access | Owns/obtains | Validates and reconciles |
| Migration transforms | Owns or jointly defines | Automates reconciliation and exceptions |
| Identity/e-sign/M365/other integrations | Owns architecture/configuration | Builds contract/failure-mode tests |
| Public disclosure/redaction rules | Owns/obtains authoritative rules | Automates tests against supplied rules |
| UAT and production approval | Owns | Builds/runs repeatable evidence gates |
| Production cutover | Owns decision and execution | Supports readiness, verification, and telemetry |

## Inputs required from the prime/SI

Before estimating effort, TJLabs needs the following inputs:

1. Selected CLM platform, edition/version, and implementation partner role.
2. Conga export format(s), object inventory, approximate record/document volumes, and representative non-sensitive samples.
3. Target import/API documentation, rate limits, attachment limits, and environment restrictions.
4. Microsoft 365/Word, e-signature, identity provider, and repository integration architecture.
5. Environments available for migration rehearsals and automated testing.
6. Prime-approved public/private classification and redaction rules.
7. Public portal/search architecture and publishing SLA requirements.
8. Required security/data-handling constraints for subcontractors.
9. Target implementation timeline, rehearsal dates, and production cutover window.
10. Named owners for migration acceptance, integrations, public publishing, security, and final go/no-go.

## Suggested delivery sequence

### Phase 0 — Discovery and interface freeze

- Confirm scope/RACI and target-platform constraints.
- Inventory source data and integration surfaces.
- Freeze acceptance metrics and evidence format.

**Exit:** no unknown critical interface or source-data class; unresolved assumptions are named risks.

### Phase 1 — Migration dry-run harness

- Implement manifests, mapping validation, reconciliation, and exception reporting.
- Run on representative extracts, then progressively larger rehearsals.

**Exit:** deterministic rerun and record/document reconciliation demonstrated.

### Phase 2 — Integration and publication automation

- Add API/interface contract tests, negative-path tests, and public publishing/redaction regressions.

**Exit:** critical interfaces and zero-tolerance public leakage cases are automated.

### Phase 3 — UAT and cutover readiness

- Bind technical checks to prime-approved end-to-end scenarios.
- Run migration rehearsal, integration gate, public publishing gate, and recovery rehearsal.

**Exit:** objective go/no-go evidence pack complete with owned exceptions.

### Phase 4 — Production verification and hypercare

- Re-run production-safe validation, monitor exceptions, and produce short-cycle evidence until the prime's stabilization criteria are met.

**Exit:** agreed service/stability thresholds met and residual risks transferred to named owners.

## Estimation model

TJLabs should estimate only after discovery inputs are available. A defensible estimate should be driven by measurable complexity rather than a fixed generic package:

- number of source object/document classes;
- total records and attachment volume;
- number and maturity of target import paths;
- number of critical external integrations;
- number/complexity of public disclosure and redaction rules;
- number of environments and rehearsals;
- cutover/hypercare duration and support windows.

This allows a prime to buy the narrow assurance workstream it needs without bundling unrelated CLM implementation responsibilities.

## Partner handoff artifact

For a first partner call, pair this document with [`PARTNER_DISCOVERY_CHECKLIST.md`](./PARTNER_DISCOVERY_CHECKLIST.md). A useful 30-minute discovery outcome is:

- confirmed platform and prime role;
- RACI for the four workstreams above;
- available source/target samples and environments;
- top three implementation risks;
- rough level of effort for a pilot/rehearsal;
- decision on whether TJLabs should prepare a formal subcontract scope.

## Reference points

- INPRS procurement page: <https://www.in.gov/inprs/about-us/procurement>
- Icertis partner directory: <https://www.icertis.com/partner/>

Icertis currently identifies Deloitte, Accenture, PwC, and MPC as certified Public Sector system-integrator partners. That certification is a useful partner-screening signal; it does not by itself establish that any listed firm is pursuing INPRS RFP 26-04.

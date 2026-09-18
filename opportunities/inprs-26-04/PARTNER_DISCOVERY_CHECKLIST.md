# INPRS RFP 26-04 — Partner Discovery Checklist

Use this checklist with a qualified CLM prime or implementation partner before TJLabs estimates or commits to the technical assurance workstream in [`TECHNICAL_WORKSTREAM.md`](./TECHNICAL_WORKSTREAM.md).

The goal of the first call is not to redesign the CLM solution. It is to determine whether a bounded migration/integration/public-publishing/test-automation workstream is useful, technically feasible, and separable from the prime's responsibilities.

## 30-minute discovery target

By the end of the call, capture:

- selected or proposed CLM platform and the partner's exact role;
- current migration approach and the highest-risk legacy data classes;
- critical external integrations and their owners;
- public publishing/search/redaction architecture;
- available test environments and representative source data;
- target rehearsal/cutover dates;
- a draft RACI for the bounded TJLabs workstream;
- top three risks that would materially change effort or feasibility;
- whether a pilot/rehearsal scope should be priced next.

## A. Prime and solution posture

1. Are you acting as prime contractor, CLM product vendor, certified SI, subcontractor, or another role?
2. Which CLM platform, edition/version, and hosting model are you proposing?
3. Who owns solution architecture, product configuration, implementation governance, and final production promotion?
4. Which portions of RFP 26-04 are you specifically considering TJLabs for?
5. What must remain inside your own delivery methodology or certified-partner boundary?

### Evidence to request

- high-level solution architecture;
- current RACI;
- implementation phase plan;
- target-platform import/API documentation that may be shared with a subcontractor.

## B. Conga/source migration

6. What Conga products/modules and adjacent repositories contain authoritative contract data today?
7. What are the approximate counts for contracts, amendments, attachments, document versions, related records, and other in-scope objects?
8. Are stable source identifiers available for every contract and document/attachment object?
9. What export mechanisms are available: bulk files, APIs, database extracts, reports, or vendor-assisted export?
10. Which source fields or object types are known to be inconsistent, custom, deprecated, or difficult to export?
11. Is there a representative non-sensitive sample that preserves the real schema and relationship structure?
12. What transformation/mapping work has already been completed, and who approves the source-to-target mapping?
13. What target import mechanisms exist, and are they idempotent or externally keyed?
14. How are failed records, partial attachment loads, and retries represented by the target platform?
15. How many full migration rehearsals are planned before production cutover?

### Migration qualification signals

Good signals:

- immutable source IDs are preserved or explicitly mapped;
- bulk extraction and target loading are repeatable;
- representative samples exist early;
- at least one non-production full-volume rehearsal is planned;
- the prime accepts record/document reconciliation as a formal gate.

Red flags requiring explicit mitigation:

- no stable source key across extracts;
- target imports silently create records on retry;
- attachments/documents are moved outside the same reconciliation model as contract metadata;
- the only validation method is manual spot checking;
- source export is not available until immediately before cutover;
- excluded or failed source records have no durable exception ledger.

## C. Microsoft 365 / Word / e-signature / identity

16. What Word/Microsoft 365 integration pattern is proposed, and where is the authoritative document during redlining?
17. Which e-signature service is in scope, and how are envelope IDs, statuses, callbacks, and executed documents linked to the CLM record?
18. Which identity provider is used for SSO/MFA, and how are groups/roles mapped into CLM permissions?
19. Are service accounts, application identities, or delegated user permissions required for integrations?
20. What are the known API limits, callback/retry semantics, and non-production credentials/environment constraints?
21. Who owns integration failures operationally after go-live?

### Integration qualification signals

Good signals:

- documented APIs/webhooks and non-production endpoints exist;
- correlation IDs can trace a business transaction across systems;
- duplicate and out-of-order callbacks are handled explicitly;
- the prime has named operational owners for each critical dependency.

Red flags requiring explicit mitigation:

- integration success is inferred only from UI state;
- no retry/idempotency contract exists;
- shared human credentials are expected for automation;
- production-only integration testing is assumed;
- e-signature/document identifiers cannot be reconciled back to the CLM record.

## D. Public contract portal, search, and redaction

22. Is the public contract experience native to the selected CLM, a separate portal, an exported dataset/search index, or a combination?
23. Who owns the authoritative rules for what is public, conditionally public, redacted, withheld, or never public?
24. Are rules applied at field, clause, document, attachment, or whole-contract level?
25. Are redactions performed before publication, at render time, in a separate copy, or by another system?
26. What surfaces must be tested for leakage: HTML/detail pages, downloads, document previews, metadata, search index, APIs/feeds, caches, or exports?
27. How quickly must create/update/unpublish actions propagate to public search?
28. Can public records be tied to an immutable internal source/version identifier for parity checks?
29. Who approves a redaction/publication test fixture as representative and legally correct?

### Publication qualification signals

Good signals:

- disclosure rules come from an authoritative owner and can be expressed as test cases;
- publication has a separate release gate;
- search index and downloadable documents can be reconciled to authoritative versions;
- unpublish/redaction changes have an explicit propagation SLA.

Red flags requiring explicit mitigation:

- legal/disclosure behavior is expected to be inferred by the test team;
- protected fields are removed only from the page UI but remain in metadata or search;
- there is no way to invalidate stale indexed/cached content;
- the public portal has no non-production or protected test path.

## E. Environments, security, and data handling

30. Which DEV/TEST/UAT/pre-production environments will be available, and when?
31. Can realistic-but-non-sensitive test data be used, or must all testing use protected production-derived data?
32. What data-handling, retention, access-control, encryption, and deletion obligations apply to subcontractors?
33. Are there restrictions on automated testing, API traffic, source exports, local processing, or logs/artifacts?
34. What evidence must be retained for audit, security review, or acceptance, and for how long?
35. What access provisioning lead time should be assumed for subcontractor personnel/services?

### Security stop conditions

Do not estimate implementation velocity as if access is solved when any of the following is unknown:

- subcontractor access approval path;
- permitted data locations/retention;
- whether representative source data may leave the prime-controlled environment;
- whether service/API identities can be provisioned for automation;
- required security review before executing test harnesses.

## F. Acceptance, cutover, and operations

36. Who owns final migration acceptance, integration acceptance, public-publishing acceptance, security approval, and production go/no-go?
37. What objective thresholds must be met for migration completeness and exception volume?
38. Which defects are zero-tolerance at go-live?
39. What is the planned cutover window, and how much rollback time exists?
40. What constitutes rollback versus proceed-with-remediation?
41. Can the rollback/recovery path be rehearsed before production?
42. How long is the hypercare period, and what support hours/response expectations apply?
43. Which telemetry or reports will exist on day one for migration exceptions, integration failures, user-journey failures, and publishing anomalies?
44. What evidence closes the implementation/hypercare phase?

### Cutover qualification signals

Good signals:

- go/no-go criteria are measurable and have named decision owners;
- rollback triggers are explicit;
- reconciliation and integration checks are rerunnable during the cutover window;
- hypercare has telemetry and thresholds rather than relying on user complaints.

Red flags requiring explicit mitigation:

- no full-volume rehearsal before production;
- no agreed rollback trigger;
- known migration exceptions are tracked only in chat/email;
- public publishing has no zero-tolerance leakage gate;
- post-go-live support lacks a way to correlate incidents to migration/integration events.

## G. Commercial/scoping questions

45. Is the partner asking for a fixed deliverable, time-and-materials support, a pilot, or an embedded engineering workstream?
46. Which artifacts are expected in the proposal versus after award?
47. What schedule milestone should a TJLabs pilot de-risk first?
48. Is the partner expecting TJLabs to supply only tooling/evidence, or also operate the tooling during rehearsals and cutover?
49. Are there required subcontract forms, insurance, security attestations, background checks, or flow-down terms that affect start date or pricing?
50. What decisions can be made before award, and which activities require formal authorization after award?

## Draft RACI to complete on the call

| Deliverable / decision | Prime/SI | CLM vendor | TJLabs | INPRS/authorized owner | Notes |
| --- | --- | --- | --- | --- | --- |
| Product/config architecture |  |  | C |  |  |
| Conga/source export |  |  | C |  |  |
| Source-to-target mapping approval |  |  | R/C |  |  |
| Migration reconciliation harness | C | C | R | I |  |
| Migration acceptance | R | C | C | A |  |
| Identity/e-sign/M365 configuration | R | C | C | C |  |
| Integration contract/failure tests | C | C | R | I |  |
| Public disclosure/redaction rules | C | C | I/test only | A |  |
| Public publishing regression tests | C | C | R | C |  |
| Cutover plan | R | C | C | A |  |
| Go/no-go decision | R/C | C | I | A |  |
| Hypercare evidence | R | C | R/C | I |  |

Legend: **R** = Responsible, **A** = Accountable, **C** = Consulted, **I** = Informed. The table is a discussion aid, not an assumed contractual allocation.

## First-call decision record

Fill this section immediately after discovery so the lead does not decay into another unstructured thread.

- **Partner / contact:**
- **Date:**
- **Partner role:**
- **Proposed CLM platform:**
- **TJLabs lane requested:**
- **Earliest useful pilot milestone:**
- **Available source sample:**
- **Available test environment:**
- **Top risk 1:**
- **Top risk 2:**
- **Top risk 3:**
- **Hard blocker:**
- **Next artifact / owner / due date:**
- **Proceed / hold / decline:**

## Boundaries

- Do not contact INPRS personnel outside the solicitation's authorized procurement channel.
- Do not imply TJLabs is the CLM prime, certified implementation partner, or product vendor unless that becomes factually true and is approved for the proposal.
- Do not infer public-record/redaction rules; test only rules supplied or approved by the responsible party.
- Do not move protected production data into a tool/environment until the applicable handling rules and authorization are explicit.
- Do not quote a fixed migration outcome until source inventory, target import behavior, rehearsal availability, and exception ownership are understood.

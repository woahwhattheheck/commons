# Draft market-information response — Pinellas County 26-0795-RFI

**Internal review draft. Not submitted.** This response is deliberately scoped to capabilities we can evidence and identifies partner dependencies instead of presenting an unbuilt platform as a production product.

## 1. Respondent positioning

Token Junkie Labs can contribute a bounded **evidence-integrity, chain-of-custody, integration and assurance architecture** for a digital evidence/exhibits platform. We would not represent this carrier as an already-deployed turnkey court evidence SaaS. For a future procurement, a production response should pair these controls with a platform/hosting provider able to evidence user-facing court workflows, U.S. infrastructure, security/compliance posture, operations/support and relevant deployments.

That distinction is useful to the County at RFI stage: it makes the integrity and interoperability requirements independently testable instead of asking the County to trust a vendor's UI or marketing claim as proof of evidentiary controls.

## 2. Functional architecture

### Authentication and access

Use federated identity for internal County/court users with role, case/hearing and workflow context. External attorneys, self-represented litigants and other authorized submitters use a separately bounded external identity flow with MFA support, explicit enrollment/recovery policy and prompt deprovisioning. Privileged administration is separated from ordinary evidence access.

Every authorization-sensitive access, including viewing an evidence file, becomes an audit event. That directly supports the RFI requirement to record activity for all file actions rather than treating reads as invisible.

### Submission and file handling

External uploads use resumable/chunked transfer, server-side size limits and quarantine before acceptance. Submitted bytes receive a content digest immediately; declared file names/MIME types remain metadata rather than trusted identity. A production platform should add current malware scanning, content-type inspection and safe media handling before promotion.

Mobile/desktop upload, common audio/video/image/document formats, pre-submission editing UX, email/SMS notifications and accessibility are production-platform capabilities that should be demonstrated by the eventual product/prime.

### Evidence vs. exhibits and physical items

The model separates immutable content identity from mutable case/exhibit metadata and workflow state. Evidence and exhibit workflows can diverge without copying or rewriting original bytes. Physical items use tracked placeholders/identifiers linked into the same custody ledger, so custody/reporting spans both digital and physical references while not pretending a physical object is a file.

### Chain of custody and accepted-evidence locking

All material actions append canonical hash-linked events. The hash chain detects non-coherent mutation but is not, by itself, proof that the observed chain is the retained original chain: a writer with authority over the whole mutable object could construct another coherent history and recompute its hashes. The reference therefore requires an independently retained custody witness binding the exact event count, chain head and current state. Verification accepts a retained history only when both semantic/hash replay and that external witness agree.

Acceptance/finalization changes the object's state so original bytes cannot be replaced; later redactions, transcodes or authorized copies are separately identified derivatives linked to the original. The supplied reference implementation demonstrates deterministic content identity, event chaining, view-event logging, acceptance lock, external-witness checking and verification failure on coherent history reseal. It is an assurance artifact, not production software or an independently trusted storage service.

### Search, inventory and reporting

A production index should expose case/hearing metadata, exhibit/evidence status, confidentiality class, retention/hold state, custody events and physical-item tags. Reports should be derivable from the authoritative ledger for custody, access, retention review, closure and destruction decisions.

### Retention, appeal and destruction

Retention policy is externally authorized configuration—not embedded vendor guesswork. Holds and releases, retention eligibility, completed notice/copy opportunity, approvals and destruction authorization are modeled as generated authority records in separately rooted snapshots. Lifecycle events retain the exact snapshot root and record generation/root they consumed. Verification must reacquire the archived snapshot and independently trusted root; merely constructing a locally consistent snapshot does not grant authority.

Holds block destruction. Eligible items enter a review state. Final destruction requires current eligible retention evidence, completed notice evidence, at least two current approvals from distinct issuers, explicit destruction authority and no active hold. The permanent-delete event survives as a receipt with content identity and exact authority-record bindings while the content is irrecoverably removed according to the approved storage design.

Appeal/records-copy exports use deterministic manifests tying exported representations back to immutable original identity and a custody-event digest.

### Case-management and court-system integration

Use an adapter layer with stable external system/case/hearing identifiers and idempotency keys. Retries must be safe: the same event cannot create a second evidence object or silently attach to another case. The actual County court/CMS products and allowed APIs are not identified in the public RFI, so a production bidder should demonstrate adapters only after those interfaces are known.

### Test/training

Maintain an isolated test/training environment with separate identities/endpoints and no live external users. Use synthetic or explicitly authorized records by default. A production provider should document how configuration is promoted between environments without copying protected production evidence.

## 3. Security/hosting answer boundary

The target production system should encrypt in transit and at rest, keep court-record storage in the United States, protect against unauthorized data use/mining, route third-party/law-enforcement access through authorized custodian processes, scan untrusted uploads, and have tested backup/recovery/DR/continuity controls.

This carrier **does not claim** a U.S. hosting certification, FedRAMP/CJIS certification, production malware service, BCP/DR history, existing County/court deployment, or a live County-controlled authority-root service. Those are partner/provider evidence gates in any future procurement.

## 4. Implementation approach for a future procurement

A credible implementation would phase delivery rather than migrate evidence in one cutover:

1. **Discovery & policy mapping:** users, case/hearing flows, retention/legal hold, current systems, file volumes/types, identity and records/security authority.
2. **Contract tests & sandbox:** API schemas, custody invariants, authorization model, quarantine/scanning, representative synthetic data and failure/recovery drills.
3. **Bounded pilot:** selected case/hearing type; limited internal/external cohort; explicit success and rollback criteria; chain-of-custody verification and records export.
4. **Migration/integration waves:** only after reconciliation tests prove case association, object digests, metadata, access control and retention state.
5. **Operational acceptance:** restore/DR exercise, access-review evidence, custody/reporting verification, training completion, support escalation and performance/size tests.

## 5. RFI limitations and assumptions

- This is market information, not a proposal or award claim.
- Controlling OpenGov packet/addenda must be re-read before any actual response upload.
- The public RFI does not identify the County's CMS/court-platform products or API contracts.
- Exact volume, concurrency, maximum file size, retention schedules, RTO/RPO, accessibility target, identity provider, security policy baseline and desired support SLA require buyer/packet authority in a future procurement or permitted clarification process.
- The reference model assumes custody witnesses and authority-snapshot roots are retained by systems outside the mutable evidence object; it does not create that institutional trust merely by hashing local data.
- TJLabs would need a production platform/hosting partner for a turnkey system unless a future solicitation explicitly procures only the bounded architecture/integration/assurance work described here.

## 6. Value to future procurement

The main recommendation is to make custody and lifecycle requirements **acceptance-testable**. Require bidders to prove that: original bytes retain stable identity; every view/action is auditable; accepted originals cannot be silently replaced; the retained event history is independently anchored rather than only self-hashed; retries cannot duplicate/misattach evidence; holds stop destruction; hold/release/retention/notice/approval/destruction authority is reconstructable from independently trusted generations; exports are verifiable; and restore/DR preserves both objects and custody history. Those tests reduce dependence on screenshots and vendor assertions and can travel across whichever commercial platform Pinellas ultimately selects.

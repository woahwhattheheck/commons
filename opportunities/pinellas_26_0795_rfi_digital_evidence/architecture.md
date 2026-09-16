# Evidence integrity reference architecture

This is a **reference architecture / integration-assurance component**, not a claim that Token Junkie Labs operates a finished court evidence SaaS.

## Core invariants

1. **Content identity is separate from metadata.** Every uploaded digital object receives a cryptographic digest over immutable original bytes. Case IDs, exhibit numbers, confidentiality labels and workflow state do not silently change evidence identity.
2. **Every material action is an event.** Submission, scan disposition, metadata edits, view/access, copy/export, status/classification change, acceptance/finalization, legal hold, retention decision and destruction authorization append events. The County RFI explicitly calls for activity on all file actions, including viewing.
3. **Event history is hash-linked and host-witnessed.** Hash links detect mutation relative to a retained head but are self-resealable in isolation. Current verification therefore also requires a witness retained outside the request caller's mutable evidence object.
4. **Accepted/finalized evidence is immutable.** Later redaction/derivative/copy operations create separately identified objects; they do not rewrite accepted originals.
5. **Current lifecycle authority is host-time-bound.** Low-level `Evidence` accepts explicit timestamps for deterministic historical replay. Current operations do not. `CurrentCustodyService` obtains a UTC instant from its captured host provider and uses that same instant for current-state verification and the transition. Future authority records cannot be made current by a request caller selecting a future timestamp.
6. **Current witness advancement is atomic.** The host provider exposes an atomic compare-and-retain operation over exact predecessor witness → successor witness. A current mutation verifies a copied candidate against the predecessor, mutates the copy, asks the host to compare-and-swap that predecessor, and exposes the local successor only after the swap succeeds. Concurrent same-predecessor writers cannot both commit.
7. **Retention and destruction are host-rooted authority transitions.** Eligibility, hold/release, notice, approvals and destruction authority are generation-bound records. Current hold/destruction gets the snapshot from the captured host provider; the request caller cannot supply a snapshot/root/trust-set extension. Verification reacquires exact archived roots referenced by retained events.
8. **The service binding is immutable under ordinary rebinding.** Provider methods and low-level types are captured into lexical closures when `CurrentCustodyService(provider)` is constructed. The returned service is an immutable tuple of public operation closures, not an object carrying writable provider-callable attributes. Ordinary later rebinding of provider methods or imported module globals does not redirect that already-bound service.
9. **Views matter.** Read access emits audit events with actor, purpose/context, object identity and authorization decision; read-only access is not invisible.
10. **External submission is untrusted input.** Uploads land in quarantine, are bounded/scanned, and client-provided MIME labels do not establish trusted type.
11. **Court/CMS systems remain systems of authority for case context unless expressly migrated.** Integration adapters use stable external IDs and idempotency keys so retries cannot duplicate submissions or attach evidence to a different case/hearing.
12. **Test/training is isolated.** No production court records or live external-user identities enter training by default. Test data is synthetic or explicitly authorized.
13. **Exports are verifiable.** Authorized copies carry object digest, requested representation, custody-window/event digest, export actor/time and authority metadata.

## Current trust boundary

The Python reference has two layers:

- `custody_reference.py` is a deterministic **integrity/historical replay primitive**. Explicit event times, `expected_witness`, snapshots and trusted roots do not authenticate themselves.
- `current_custody_service.py` is the **current-positive composition boundary**. It captures five host capabilities once: current UTC time, retained predecessor witness, atomic compare-and-retain witness advancement, current authority snapshot and archived authority snapshot retrieval.

Per-operation callers can supply business event inputs such as actor, purpose, status, bytes and authority evidence IDs. They cannot supply time, witnesses, snapshots, trusted roots or trust-set members. Before mutation, the service copies the caller object and verifies that copy against the exact retained predecessor and host current time. After mutation, the host must atomically advance that exact predecessor to the candidate witness. Only then does the caller object receive the successor state.

The provider is deliberately an integration contract, not a new authentication/authorization subsystem. The reference does not claim that Python can manufacture institutional trust. A production host should back it with its existing retained ledger/records system, transactional/conditional storage, authenticated append-only service or equivalent County-controlled source.

The ordinary-rebinding claim is intentionally narrow and testable: once a service is constructed, replacing provider object methods, imported `Evidence`/`AuthoritySnapshot`/`CustodyError` globals, or the module's factory name does not retarget that existing service, and its public operation fields cannot be reassigned. Arbitrary closure inspection, mutation through reflective interpreter facilities, source replacement, debugger access or a malicious host provider is outside this reference boundary and must be controlled by the deployment environment.

## Logical components

- **Submission edge:** browser/mobile upload, resumable transfer, notification hooks, quarantine status.
- **Identity/security edge:** SSO for internal identities; MFA-capable external identity flow; provisioning/deprovisioning; role + case/workflow authorization.
- **Object store:** immutable originals plus separately identified derivatives; U.S.-residency policy at infrastructure layer.
- **Custody ledger:** append-only event stream, independently retained witness and deterministic verification/export service.
- **Authority evidence store:** retained roots/generations for holds, releases, schedule eligibility, notice, approvals and destruction authority.
- **Workflow service:** evidence/exhibit status, confidentiality/restriction, review, hearing/jury presentation, physical-item placeholders, appeal/records retrieval.
- **Records service:** retention schedules, holds, review queues, notice/copy window, approval-bound destruction.
- **Integration gateway:** case/hearing lookup, CMS adapters, webhooks/events, notification adapter and API rate/idempotency controls.
- **Security pipeline:** malware scanning/quarantine, encryption/key management, telemetry, backup/restore and DR validation.
- **Admin/reporting:** inventory, search/filter, audit/custody reports, retention/destruction queues and role administration.

## Integration contract

A production response should ask Pinellas to identify its authoritative court/case systems and permitted integration mechanism during a future procurement. The adapter should minimally preserve external system + case/hearing ID, evidence object ID + immutable digest, submitter/actor context, idempotency key, lifecycle status, source event ID/time and custody verification receipt.

Unknown CMS vendor/API details are a dependency, not a reason to fabricate an integration claim in an RFI.

## What a platform/hosting partner must prove

A turnkey response requires evidence TJLabs does not currently claim here: production-scale upload/UI workflows; U.S.-based hosting; applicable court/criminal-justice policy compliance; operational malware scanning; enterprise IAM integrations; tested backup/restore and DR; production support/SLA; major-media compatibility; accessibility; court deployments/references; and exact pricing/licensing.

# Evidence integrity reference architecture

This is a **reference architecture / integration-assurance component**, not a claim that Token Junkie Labs operates a finished court evidence SaaS.

## Core invariants

1. **Content identity is separate from metadata.** Every uploaded digital object receives a cryptographic content digest over the immutable original bytes. Case IDs, exhibit numbers, confidentiality labels and workflow state are metadata that may evolve; they do not silently change evidence identity.
2. **Every material action is an event.** Submission, virus-scan disposition, metadata edits, view/access, copy/export, status/classification change, acceptance/finalization, legal hold, retention decision and destruction authorization append events. The County RFI explicitly calls for activity on all file actions, including viewing.
3. **Event history is hash-linked and host-witnessed.** Each event commits to the prior event hash, canonical payload, actor and UTC timestamp. Hash linking alone is self-resealable and therefore does not prove which coherent history was retained. Current verification must also match a witness retained outside the request caller's mutable evidence object, binding exact event count, chain head and current state. Reorder/deletion/mutation fails semantic/hash replay; a coherent fully rehashed alternate history fails the retained host witness.
4. **Accepted/finalized evidence is immutable.** A workflow lock blocks byte replacement. Later redaction/derivative/copy operations create separately identified objects linked to the original; they do not rewrite original bytes.
5. **Retention and destruction are host-rooted authority transitions, not request booleans.** Eligibility comes from a schedule record; legal hold/release comes from authority evidence; notice/copy completion, approvals and destruction authority are generated records. Lifecycle events bind the exact authority snapshot root plus each record generation/root. The current service gets the snapshot from its host provider; an operation caller cannot supply a snapshot or trusted root. Verification reacquires archived snapshot bytes through that same captured provider. Final destruction requires current eligible retention evidence, completed notice evidence, at least two current approvals from distinct issuers, explicit destruction authority, and no active hold.
6. **Views matter.** Read access emits audit events with actor, purpose/context, object identity and authorization decision; the system should not treat read-only access as invisible.
7. **External submission is untrusted input.** Uploads land in quarantine, are size/type bounded and scanned before being promoted into the managed evidence store. Client-provided MIME names do not establish trusted type.
8. **Court/CMS systems remain systems of authority for case context unless expressly migrated.** Integration adapters use stable external IDs and idempotency keys so retries cannot duplicate submissions or silently attach evidence to a different case/hearing.
9. **Test/training is isolated.** No production court records or live external-user identities enter training by default. Test data is synthetic or explicitly authorized, and the environment has separate credentials/endpoints.
10. **Exports are verifiable.** Authorized copies carry a manifest with object digest, requested representation, custody-window/event digest, export actor, time and authority so downstream consumers can verify origin without modifying the managed original.

## Trust-root boundary

The Python reference has two layers:

- `custody_reference.py` is a deterministic **integrity/replay primitive**. Its explicit `expected_witness`, snapshot and root inputs do not authenticate themselves. They are appropriate for historical replay, tests, and use *behind* an already established host boundary.
- `current_custody_service.py` is the **current-positive composition boundary**. `CurrentCustodyService` captures a host-installed provider once. Per-operation callers never supply or extend the witness, authority snapshots, or trusted-root set. Existing state is checked against the host-retained witness before mutation; successor state is first written to the host witness store and only then exposed locally. Hold/destruction uses the provider's current snapshot, while verification reacquires every archived snapshot referenced by the event history.

The provider is intentionally an integration contract, not a new authentication/authorization subsystem. The reference does not claim to prove institutional trust from local Python values. A production host should back the provider with its existing retained ledger/records system, authenticated append-only store, signed authority service, or equivalent County-controlled source, and retain historical generations required to verify prior transitions.

This split closes the caller-self-root path: constructing a well-formed `AuthoritySnapshot`, choosing its `.root`, or computing a fresh `Evidence.witness()` can exercise low-level integrity replay but cannot advance or verify the current service because none of those values are request parameters there.

## Logical components

- **Submission edge:** browser/mobile upload, chunked resumable transfer, notification hooks, quarantine status.
- **Identity/security edge:** SSO for internal identities; MFA-capable external identity flow; provisioning/deprovisioning; role + case/workflow authorization.
- **Object store:** immutable originals plus separately identified derivatives; U.S.-residency requirement enforced at infrastructure policy layer.
- **Custody ledger:** append-only event stream, independently retained chain witness and deterministic verification/export service.
- **Authority evidence store:** retained roots/generations for holds, releases, schedule eligibility, notice, approvals and destruction authority; this is separate from the evidence object's mutable state.
- **Workflow service:** evidence/exhibit status, confidentiality/restriction, review, hearing/jury presentation, physical-item placeholders, appeal/records retrieval.
- **Records service:** retention schedules, holds, review queues, notice/copy window, approval-bound destruction.
- **Integration gateway:** case/hearing lookup, CMS adapters, webhooks/events, notification adapter and API rate/idempotency controls.
- **Security pipeline:** malware scanning/quarantine, encryption/key management, security telemetry, backup/restore and DR validation.
- **Admin/reporting:** inventory, search/filter, audit/custody reports, retention/destruction queues and role administration.

## Integration contract

A production response should ask Pinellas to identify its authoritative court/case systems and permitted integration mechanism during a future procurement. The adapter should minimally preserve:

- external system + case/hearing ID;
- evidence/exhibit object ID + immutable content digest;
- submitter/actor authority and tenant/context;
- idempotency key for retries;
- canonical lifecycle status;
- event timestamp + source event ID;
- link to custody verification receipt.

Unknown CMS vendor/API details are a dependency, not a reason to fabricate an integration claim in an RFI.

## What a platform/hosting partner must prove

A turnkey response requires evidence TJLabs does not currently claim in this carrier: production-scale upload/UI workflows; U.S.-based hosting topology; applicable court/criminal-justice policy compliance; operational malware scanning; enterprise IAM integrations; tested backup/restore and disaster recovery; production support/SLA; major-media compatibility at expected sizes; accessibility; court deployments/references; and exact pricing/licensing.

Current verification replays custody event semantics, rejects divergence between current state and the hash-linked history, reacquires authority generations through the captured host provider, and requires the host-retained custody witness for the exact history/state generation.

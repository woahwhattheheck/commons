# Evidence integrity reference architecture

This is a **reference architecture / integration-assurance component**, not a claim that Token Junkie Labs operates a finished court evidence SaaS.

## Core invariants

1. **Content identity is separate from metadata.** Every uploaded digital object receives a cryptographic content digest over the immutable original bytes. Case IDs, exhibit numbers, confidentiality labels and workflow state are metadata that may evolve; they do not silently change evidence identity.
2. **Every material action is an event.** Submission, virus-scan disposition, metadata edits, view/access, copy/export, status/classification change, acceptance/finalization, legal hold, retention decision and destruction authorization append events. The County RFI explicitly calls for activity on all file actions, including viewing.
3. **Event history is tamper-evident.** Each event commits to the prior event hash, canonical payload, actor, authority and UTC timestamp. Verification replays the chain from genesis and fails on reorder, deletion or mutation.
4. **Accepted/finalized evidence is immutable.** A workflow lock blocks byte replacement. Later redaction/derivative/copy operations create separately identified objects linked to the original; they do not rewrite original bytes.
5. **Retention and destruction are authority transitions, not delete buttons.** Eligibility is calculated from an external authorized schedule; legal hold blocks destruction. Final destruction requires explicit approval records and a notice/copy-opportunity state when the governing policy requires it. The permanent-delete action records what was destroyed, which authority approved it, and the surviving ledger/receipt.
6. **Views matter.** Read access emits audit events with actor, purpose/context, object identity and authorization decision; the system should not treat read-only access as invisible.
7. **External submission is untrusted input.** Uploads land in quarantine, are size/type bounded and scanned before being promoted into the managed evidence store. Client-provided MIME names do not establish trusted type.
8. **Court/CMS systems remain systems of authority for case context unless expressly migrated.** Integration adapters use stable external IDs and idempotency keys so retries cannot duplicate submissions or silently attach evidence to a different case/hearing.
9. **Test/training is isolated.** No production court records or live external-user identities enter training by default. Test data is synthetic or explicitly authorized, and the environment has separate credentials/endpoints.
10. **Exports are verifiable.** Authorized copies carry a manifest with object digest, requested representation, custody-window/event digest, export actor, time and authority so downstream consumers can verify origin without modifying the managed original.

## Logical components

- **Submission edge:** browser/mobile upload, chunked resumable transfer, notification hooks, quarantine status.
- **Identity/security edge:** SSO for internal identities; MFA-capable external identity flow; provisioning/deprovisioning; role + case/workflow authorization.
- **Object store:** immutable originals plus separately identified derivatives; U.S.-residency requirement enforced at infrastructure policy layer.
- **Custody ledger:** append-only event stream and deterministic verification/export service.
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


Verification replays the custody event semantics and rejects divergence between current state and the hash-chained history.

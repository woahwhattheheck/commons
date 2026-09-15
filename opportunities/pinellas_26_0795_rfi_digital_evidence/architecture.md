# Evidence integrity reference architecture

This is a **reference architecture / integration-assurance component**, not a claim that Token Junkie Labs operates a finished court evidence SaaS.

## Core invariants

1. **Content identity is separate from metadata.** Every uploaded digital object receives a cryptographic content digest over the immutable original bytes. Case IDs, exhibit numbers, confidentiality labels and workflow state are metadata that may evolve; they do not silently change evidence identity.
2. **Every material action is an event.** Submission, virus-scan disposition, metadata edits, view/access, copy/export, status/classification change, acceptance/finalization, legal hold, retention decision and destruction authorization append events. The County RFI explicitly calls for activity on all file actions, including viewing.
3. **Event history is hash-linked and externally witnessed.** Each event commits to the prior event hash, canonical payload, actor and UTC timestamp. Hash linking alone is self-resealable and therefore does not prove which coherent history was retained. Verification must also match an independently retained witness binding the exact event count, chain head and current state. Reorder/deletion/mutation fails semantic/hash replay; a coherent fully rehashed alternate history fails the external witness.
4. **Accepted/finalized evidence is immutable.** A workflow lock blocks byte replacement. Later redaction/derivative/copy operations create separately identified objects linked to the original; they do not rewrite original bytes.
5. **Retention and destruction are externally rooted authority transitions, not delete buttons.** Eligibility comes from an authorized schedule record; legal hold/release comes from authority evidence; notice/copy completion, approvals and destruction authority are exact generated records. Lifecycle events bind the exact authority snapshot root plus each record generation/root. Verification reacquires archived snapshot bytes and requires the snapshot root to be independently trusted. Final destruction requires current eligible retention evidence, completed notice evidence, at least two current approvals from distinct issuers, explicit destruction authority, and no active hold.
6. **Views matter.** Read access emits audit events with actor, purpose/context, object identity and authorization decision; the system should not treat read-only access as invisible.
7. **External submission is untrusted input.** Uploads land in quarantine, are size/type bounded and scanned before being promoted into the managed evidence store. Client-provided MIME names do not establish trusted type.
8. **Court/CMS systems remain systems of authority for case context unless expressly migrated.** Integration adapters use stable external IDs and idempotency keys so retries cannot duplicate submissions or silently attach evidence to a different case/hearing.
9. **Test/training is isolated.** No production court records or live external-user identities enter training by default. Test data is synthetic or explicitly authorized, and the environment has separate credentials/endpoints.
10. **Exports are verifiable.** Authorized copies carry a manifest with object digest, requested representation, custody-window/event digest, export actor, time and authority so downstream consumers can verify origin without modifying the managed original.

## Trust-root boundary

The supplied Python reference demonstrates the data contract at the evidence-system boundary; it is not itself a court PKI, records-authority service or immutable ledger. Two values must be retained outside the mutable `Evidence` object:

- a custody witness for the accepted event-history generation; and
- trusted roots for the exact authority snapshots used by hold/release/destruction transitions.

Possession of snapshot bytes is not trust. A caller-generated snapshot whose root is absent from the independent trust store is rejected even if every record is internally well-formed and all event hashes are recomputed. A production design should obtain these roots from an authenticated append-only store, signed authority service, or equivalent County-controlled system and retain historical generations required to verify prior transitions.

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

Verification replays custody event semantics, rejects divergence between current state and the hash-linked history, checks authority events against independently trusted snapshot generations, and finally requires an independently retained custody witness for the exact history/state generation.

# Evidence integrity reference architecture

This is a **reference architecture / integration-assurance component**, not a claim that Token Junkie Labs operates a finished court evidence SaaS.

## Core invariants

1. **Content identity is separate from metadata.** Every uploaded object receives a cryptographic content digest over immutable original bytes. Case IDs, exhibit numbers, confidentiality labels and workflow state do not silently change evidence identity.
2. **Every material action is an event.** Submission, scan disposition, metadata edits, view/access, copy/export, status/classification change, acceptance/finalization, legal hold, retention decision and destruction authorization append events. The County RFI explicitly calls for activity on all file actions, including viewing.
3. **Current history is hash-linked and host-witnessed.** Hash links detect mutation relative to a retained head but are self-resealable in isolation. Current verification therefore also requires an exact witness retained outside the request caller's mutable evidence object.
4. **Accepted/finalized evidence is immutable.** Later redaction/derivative/copy operations create separately identified objects; they do not rewrite accepted originals.
5. **Current time belongs to the host boundary.** Low-level replay accepts explicit event times for deterministic historical analysis. Current request operations do not. The current service obtains one canonical UTC instant from its captured host provider, uses it to verify the predecessor and construct the transition, then verifies the successor against that same current instant before commit. Future authority cannot be promoted by a request-selected clock.
6. **Current witness advancement is atomic.** The host provider exposes exact expected-predecessor → successor compare-and-retain semantics. A current mutation verifies a copied candidate against the predecessor, constructs and fully re-verifies the successor, atomically advances the witness, and exposes local successor state only after that CAS succeeds. Concurrent same-predecessor writers cannot both commit.
7. **Retention and destruction are host-rooted authority transitions.** Eligibility, hold/release, notice, approvals and destruction authority are generation-bound records. Current hold/destruction obtains the snapshot from the host provider; request callers cannot supply a snapshot, root or trusted-root extension. Verification reacquires exact archived snapshot generations referenced by retained events and recomputes their record/snapshot roots inside the current authority graph.
8. **The current semantic graph does not late-delegate to mutable low-level authority helpers.** `custody_reference.py` remains the historical/integrity model. The current service independently implements canonical timestamp validation, authority-record/snapshot roots, event hashing, witness generation, semantic replay and transition construction. Ordinary late rebinding of the previously exploitable low-level `_utc`, `AuthoritySnapshot.bind_current`/root, `AuthorityRecord.root`, or `Evidence.verify`/witness methods does not retarget an already constructed current service.
9. **Views matter.** Read access emits audit events with actor, purpose/context, object identity and authorization decision; read-only access is not invisible.
10. **External submission is untrusted input.** Uploads land in quarantine, are bounded/scanned, and client-provided MIME labels do not establish trusted type.
11. **Court/CMS systems remain systems of authority for case context unless expressly migrated.** Integration adapters use stable external IDs and idempotency keys so retries cannot duplicate submissions or attach evidence to a different case/hearing.
12. **Test/training is isolated.** No production court records or live external-user identities enter training by default. Test data is synthetic or explicitly authorized.
13. **Exports are verifiable.** Authorized copies carry object digest, requested representation, custody-window/event digest, export actor/time and authority metadata.

## Historical primitive vs current-positive composition

The supplied Python reference has two deliberate layers.

`custody_reference.py` is the **deterministic historical/integrity primitive**. Explicit timestamps, `expected_witness`, snapshots and trusted roots are inputs to replay. Possession of well-formed values is not itself current trust.

`current_custody_service.py` is the **current-positive composition boundary**. The public factory accepts one host provider and current operations accept business-event inputs only. They do not accept current time, witness, snapshot, trusted root or trust-set members.

The provider supplies:

- canonical current UTC time;
- the retained predecessor witness;
- atomic compare-and-retain of predecessor → successor witness;
- the current authority snapshot; and
- archived authority snapshot generations.

The module constructs the public factory from captured low-level data types plus canonical hashing/JSON/time/object primitives. Current verification and mutation do not call the low-level authority-affecting methods that previously allowed transitive rebinding. On each existing-object mutation, the service:

1. acquires host current time and retained predecessor witness;
2. clones caller state without using the low-level mutation methods;
3. independently verifies the complete predecessor chain/state/witness and all archived authority bindings against host time;
4. constructs the candidate transition using the same host time;
5. independently verifies the complete successor, including any new authority binding, against that same time and the successor witness;
6. atomically advances the exact predecessor witness to the successor through the host; and
7. only then copies the successor state to the caller-visible object.

A newly supplied current snapshot must already be retrievable from the host's archived-snapshot surface by the recomputed root before a transition that references it can commit. This prevents a transition from committing an authority generation the verifier cannot subsequently reacquire.

The boundary is intentionally narrower than an interpreter sandbox. Arbitrary closure-cell manipulation, debugger/interpreter compromise, source replacement or a malicious host provider are deployment/infrastructure concerns, not authority guarantees claimed by this Python reference. The code also does not create authentication, credentials, ACLs, user admission or another authorization subsystem.

## Logical components

- **Submission edge:** browser/mobile upload, resumable transfer, notification hooks, quarantine status.
- **Identity/security edge:** SSO for internal identities; MFA-capable external identity flow; provisioning/deprovisioning; role + case/workflow authorization.
- **Object store:** immutable originals plus separately identified derivatives; U.S.-residency policy at infrastructure layer.
- **Custody ledger:** append-only event stream, independently retained witness and deterministic verification/export service.
- **Authority evidence store:** retained generations for holds, releases, schedule eligibility, notice, approvals and destruction authority.
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

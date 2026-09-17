# OneWriter product specification

## Product promise

Given a proposed external action, OneWriter answers one narrow question with reconstructable evidence:

> **Who, if anyone, owns the right to perform this exact outbound action now?**

It does not send. It prevents duplicate writers, preserves the distinction between provider events and human outcomes, and makes stale work recoverable without guessing.

## Authority boundary

The repository engine and bundled fixture are an **offline semantic contract**, not an authentication provider.

- In the synthetic fixture, `actor`, `role`, `at`, provider references, and human-event references are trusted test facts.
- In a deployed app, the backend must derive the authenticated actor and role, stamp authoritative UTC time, and bind provider/human evidence through authenticated adapters. Those fields must never be accepted as caller authority merely because the JSON shape is valid.
- The receipt chain detects changes to retained bytes. It is not a digital signature and does not independently prove that a provider or human event occurred.
- OneWriter coordinates authority before an external action. It never sends email, DMs, forms, bids, submissions, or payments.

## Identity and collision key

A lane is defined by exactly five normalized fields: organization, domain, route, purpose, and opportunity. The backend derives a SHA-256 collision key from canonical normalized JSON.

Normalization is NFKC, case-folded, whitespace-collapsed, and control/format/line-separator rejecting. Cosmetic casing, duplicate spaces, `https://`, `www.`, full-width aliases, and route casing must not create parallel lanes. Unsupported extra identity fields are rejected rather than silently ignored.

## Authenticated roles

- **WORKER** — proposes work, acquires or releases a bounded lease, and records provider outcomes while holding an active unexpired lease.
- **SYSTEM** — performs explicit stale expiry using backend time. The canonical system actor is not client-selectable.
- **HUMAN_SOURCE** — records an authenticated human event that may reopen a sent lane.
- **OPERATOR** — places a policy hold.
- **Backend clock** — stamps event time and enforces monotonic replay order. A client cannot clear another worker by supplying a future timestamp.

The offline replay validates this role/action contract. Production must additionally authenticate the role and evidence source.

## Screens

### 1. Control room

Top metrics: active leases, collisions prevented, duplicate touches prevented, stale lanes recovered, dead routes, human reopens. Below: live lanes sorted by risk with search/filter chips.

### 2. Propose lane

Form fields exactly match the collision identity. Before commit, show normalized values and collision-key preview. Existing state is surfaced instead of silently creating a duplicate record.

### 3. Lane detail

Readable identity, state badge, active holder/expiry, lease return state, provider/human evidence references, allowed next actions, denial explanations, and reverse-chronological receipts. Each receipt exposes event, prior, and receipt digest prefixes.

### 4. Collision moment

Show two demo workers claiming the same lane: winner receipt, denied writer, `active_lease` reason, and a concise explanation that no external send has occurred.

### 5. Receipt inspector

Replay chronologically. A Verify Chain action recomputes event and receipt hashes. A local demo-only tamper preview may demonstrate verification failure without changing canonical history. The UI must state that hash-chain integrity is not provider authentication.

## State semantics

- `CLEAR` — eligible for one bounded lease and not carrying a prior-send reopen fence.
- `LEASED` — one holder only. The lease records both expiry and `lease_return_state`.
- `SENT_DNR` — provider evidence was retained for a send; no duplicate acquisition until a genuine human event.
- `DEAD_ROUTE` — provider evidence was retained for route failure; never label this buyer rejection.
- `HUMAN_EVENT_REOPEN` — one evidenced human event opened one bounded next-action slot. Releasing or expiring that lease returns to `HUMAN_EVENT_REOPEN`, not `CLEAR`, so the original do-not-resend fence is not silently erased.
- `HOLD` — authenticated operator fence; no acquisition.

Canonical transitions and invariants are in `state_machine.json`.

## Lease and time rules

- Lease duration is an integer from 1 through 3600 seconds.
- A second worker is denied while the lease is active.
- Once time reaches expiry, the holder can no longer release or record provider SENT/BOUNCE.
- An expired lease is not silently stolen. Acquisition remains denied until a `SYSTEM` expiry event explicitly returns the lane to its recorded return state.
- `EXPIRE_LEASE` uses backend time and is denied before the recorded expiry.
- Event time may stay equal but may never move backward within one replay generation.

## Evidence and receipts

Suggested collections:

- `lanes`: collision key (unique), normalized/display identities, state, lease holder, expiry, return state, timestamps.
- `events`: immutable unique event ID, backend timestamp, authenticated actor/role, action, canonical lane, and evidence-bearing input.
- `receipts`: append-only sequence, event digest, state decision, prior receipt digest, and receipt digest.

Each accepted or denied semantic event produces a receipt binding:

- canonical event ID, backend time, actor, role, action, and collision key;
- complete normalized lane;
- lease duration;
- provider evidence reference;
- human-event evidence reference;
- accepted/denied decision, prior state, next state, and reason;
- SHA-256 of the canonical decision input;
- prior receipt digest and current receipt digest.

Receipt writes occur in the same transaction as state decisions. Event IDs are unique at the engine boundary. Unknown event fields are rejected rather than omitted from the retained decision record.

## Atomicity requirement

Lease acquisition must be a compare-and-set/transaction against the canonical lane row. A UI check followed by a later write is insufficient. Two concurrent requests must not both receive `LEASED`.

The deterministic Python engine proves transition semantics, evidence binding, and replay integrity. It does **not** itself prove a deployed database transaction; the deployed app must exercise a real concurrent backend race.

## Required demo controls

- Reset bundled synthetic fixture.
- Run next event / run full replay.
- Simulate two simultaneous backend acquisition calls.
- Advance through explicit system expiry without changing the client clock.
- Record synthetic SENT, BOUNCE, and HUMAN_EVENT evidence references.
- Verify event and receipt digests.
- Export JSON containing lanes, metrics, and receipts.

## Acceptance criteria

1. Equivalent normalized identities produce one collision key.
2. Invisible/control-bearing identity aliases and unsupported identity fields are rejected.
3. Two concurrent lease acquisitions can never both succeed in the deployed transactional backend.
4. Lease duration is an integer from 1 through 3600 seconds.
5. Event IDs are unique and event time never moves backward.
6. A client/worker cannot self-assert SYSTEM expiry authority.
7. A lease cannot expire before its recorded expiry.
8. An expired holder cannot release or record provider SENT/BOUNCE.
9. An expired lane cannot be reacquired until explicit SYSTEM recovery.
10. Only the active unexpired lease holder can record provider SENT/BOUNCE or release.
11. Provider outcome requires a non-empty retained evidence reference.
12. `PROVIDER_SENT` yields `SENT_DNR` and blocks a new lease.
13. An evidenced `HUMAN_EVENT` from `HUMAN_SOURCE` may reopen `SENT_DNR`.
14. A reopened lease returns to `HUMAN_EVENT_REOPEN` on release/expiry rather than losing the send fence.
15. `PROVIDER_BOUNCE` yields `DEAD_ROUTE`, never buyer rejection.
16. `DEAD_ROUTE` is not reopened by the sent-lane human-event shortcut; a changed route is a distinct lane identity.
17. Only `OPERATOR` can place a hold.
18. Denied attempts are retained as receipts.
19. Receipt digests bind all normalized decision input and form a verifiable chain from `GENESIS`.
20. Tampering with an evidence reference, event input, decision, or chain link is detected.
21. Public demo contains only synthetic `.example` organizations/routes.
22. No action performs real email, DM, form submission, procurement submission, contest submission, or payment mutation.
23. Exported demo state matches the deterministic semantics in `acceptance.py` / `demo_events.json`.
24. Both normal Python and optimized `python -O` execute a positive number of hostile tests through retained Commons CI.

## Out of scope

Real customer CRM sync, provider sending, mailbox credentials, scraping, payment processing, autonomous contact, private lead import, cryptographic identity/signature infrastructure, and replacement of the team's existing production Muse/outbound authority controls.

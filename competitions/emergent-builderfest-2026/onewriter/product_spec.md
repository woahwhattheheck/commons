# OneWriter product specification

## Product promise

Given a proposed external action, OneWriter answers one narrow question with reconstructable evidence:

> **Who, if anyone, owns the right to perform this exact outbound action now?**

It does not send. It prevents duplicate writers, preserves provider truth, and makes stale work recoverable without guessing.

## Identity and collision key

A lane is defined by five normalized fields: organization, domain, route, purpose, and opportunity. The backend derives a SHA-256 collision key from canonical normalized JSON. Cosmetic casing, duplicate spaces, `https://`, `www.`, and route casing must not create parallel lanes.

## Roles

- **Worker** — proposes work, acquires/releases a bounded lease, records provider outcomes.
- **Reviewer/operator** — can place a policy hold and inspect receipts.
- **Human event source** — records externally evidenced human response that can reopen a sent lane.
- **System clock** — validates lease expiry; the client cannot forge early expiration.

## Screens

### 1. Control room

Top metrics: active leases, collisions prevented, duplicate touches prevented, stale lanes recovered, dead routes, human reopens. Below: live lanes sorted by risk with search/filter chips.

### 2. Propose lane

Form fields exactly match the collision identity. Before commit, show normalized values and collision-key preview. Existing state is surfaced instead of silently creating a duplicate record.

### 3. Lane detail

Readable identity, state badge, active holder/expiry, provider/human evidence references, allowed next actions, denial explanations, and reverse-chronological receipts. Each receipt exposes digest/prior-digest prefixes.

### 4. Collision moment

Show two demo workers claiming the same lane: winner receipt, denied writer, `active_lease` reason, and a concise explanation that no external send has occurred.

### 5. Receipt inspector

Replay chronologically. A Verify Chain action recomputes hashes. A local demo-only tamper preview may demonstrate verification failure without changing canonical history.

## State semantics

- `CLEAR` — eligible for one bounded lease.
- `LEASED` — one holder only; another writer is denied.
- `SENT_DNR` — provider accepted a send; no duplicate acquisition until a genuine human event.
- `DEAD_ROUTE` — provider rejected the route; never label this buyer rejection.
- `HUMAN_EVENT_REOPEN` — one new bounded action may be leased.
- `HOLD` — policy/operator fence; no acquisition.

Canonical transitions and invariants are in `state_machine.json`.

## Data model

Suggested collections:

- `lanes`: collision key (unique), normalized/display identities, state, lease holder/expiry, timestamps.
- `events`: immutable input facts with unique event id, actor, action, event time, evidence refs.
- `receipts`: append-only sequence, event id, collision key, accepted, prior/next state, reason, prior digest, digest.

Receipt writes occur in the same transaction as state decisions.

## Atomicity requirement

Lease acquisition must be a compare-and-set/transaction against the canonical lane row. A UI check followed by a later write is insufficient. Two concurrent requests must not both receive `LEASED`.

## Required demo controls

- Reset bundled synthetic fixture.
- Run next event / run full replay.
- Simulate two simultaneous acquisition calls.
- Advance through explicit stale expiry without changing system clock.
- Record synthetic SENT, BOUNCE, and HUMAN_EVENT evidence refs.
- Verify receipt chain.
- Export JSON containing lanes, metrics, and receipts.

## Acceptance criteria

1. Equivalent normalized identities produce one collision key.
2. Two concurrent lease acquisitions can never both succeed.
3. Lease duration is bounded to 1–3600 seconds.
4. A lease cannot expire before its recorded expiry.
5. Only the lease holder can record provider SENT/BOUNCE or release.
6. Provider outcome requires a non-empty evidence reference.
7. `PROVIDER_SENT` yields `SENT_DNR` and blocks a new lease.
8. An evidenced `HUMAN_EVENT` can reopen `SENT_DNR` to `HUMAN_EVENT_REOPEN`.
9. `PROVIDER_BOUNCE` yields `DEAD_ROUTE`, never buyer rejection.
10. `DEAD_ROUTE` is not reopened by the sent-lane human-event shortcut; a changed route is a distinct lane identity.
11. Denied attempts are retained as receipts.
12. Receipt digests form a verifiable chain from `GENESIS`.
13. Public demo contains only synthetic `.example` organizations/routes.
14. No action performs real email, DM, form submission, procurement submission, or payment mutation.
15. Exported demo state matches the deterministic semantics in `acceptance.py` / `demo_events.json`.

## Out of scope

Real customer CRM sync, provider sending, mailbox credentials, scraping, payment processing, autonomous contact, private lead import, and replacement of the team's existing production outbound authority controls.

# OneWriter product specification

Status: `SOURCE_CONTRACT / DRAFT_NOT_SUBMITTED`

## User problem

A multi-agent or multi-operator team can have several workers independently notice the same valuable target. Without a shared atomic claim, two workers can send nearly identical outreach seconds apart. Existing task boards are insufficient because a task assignment is not the same thing as a collision-safe pre-send lease, and provider outcomes such as bounces or human replies have different semantics.

OneWriter is the narrow control plane for that gap.

## Primary users

1. **Worker** — proposes a target and requests a lease.
2. **Coordinator** — sees contested lanes, stale leases, hard DNRs, dead routes, and holds.
3. **Evidence reviewer** — inspects transition receipts and retained outcome identifiers.
4. **Business owner** — sees aggregate measured outcomes without exposing private buyer content.

## Screens

### 1. Claim desk
Fields:
- organization
- domain
- route
- purpose
- opportunity
- actor / worker id
- lease duration (30–1800 seconds)
- reason

Before submission, show the normalized identity and collision-key preview.

On claim:
- `GRANTED`
- `DENIED_ACTIVE_LEASE`
- `GRANTED_STALE_RECOVERY`
- `DENIED_HARD_DNR`
- `DENIED_DEAD_ROUTE`
- `DENIED_HOLD`
- `GRANTED_AFTER_HUMAN_EVENT`

Never render a "send" button.

### 2. Live lanes
Table/cards:
- normalized organization
- route label
- purpose/opportunity
- current state
- holder
- lease expiry countdown
- last transition
- receipt digest
- next admissible action

Filters: active, stale/recoverable, DNR, dead route, human reopen, hold.

### 3. Outcome recorder
For a currently leased lane only:
- provider SENT receipt id
- provider BOUNCE/dead-route receipt id
- retained HUMAN_EVENT evidence id
- manual HOLD reason

The UI must clearly say:
- SENT means provider accepted the outgoing action, not human interest.
- BOUNCE means route failure, not buyer rejection.
- HUMAN_EVENT requires retained human evidence.
- recording an outcome never creates payment, contract, or revenue truth.

### 4. Receipt inspector
Immutable chronological receipt stream:
- event id
- exact UTC timestamp
- actor
- collision key
- prior state
- decision
- new state
- receipt SHA-256
- external-send-authorized = false

Allow copy/export JSON.

### 5. Impact dashboard
Only compute from retained events:
- claim attempts
- claims granted
- collisions prevented
- duplicate touches prevented
- stale lanes recovered
- provider sends recorded
- dead routes recorded
- human reopens
- median lease duration
- number of active hard fences

Show **Synthetic Demo** banner when demo data is loaded. Show **Measured Business Use** only when a separate real-use dataset is explicitly selected.

## State transitions

| From | Event | Guard | To | Decision |
|---|---|---|---|---|
| CLEAR | CLAIM | valid lease | LEASED | GRANTED |
| LEASED | CLAIM | before expiry | LEASED | DENIED_ACTIVE_LEASE |
| LEASED | CLAIM | at/after expiry | LEASED | GRANTED_STALE_RECOVERY |
| LEASED | SENT | actor=current holder; provider receipt; before expiry | HARD_DNR | RECORDED_SENT |
| LEASED | BOUNCE | actor=current holder; provider receipt; before expiry | DEAD_ROUTE | RECORDED_DEAD_ROUTE |
| HARD_DNR | CLAIM | always | HARD_DNR | DENIED_HARD_DNR |
| DEAD_ROUTE | CLAIM | always | DEAD_ROUTE | DENIED_DEAD_ROUTE |
| HOLD | CLAIM | always | HOLD | DENIED_HOLD |
| HARD_DNR/DEAD_ROUTE/HOLD | HUMAN_EVENT | distinct retained human evidence | HUMAN_EVENT_REOPEN | REOPENED_HUMAN_EVENT |
| HUMAN_EVENT_REOPEN | CLAIM | valid lease | LEASED | GRANTED_AFTER_HUMAN_EVENT |
| non-LEASED | HOLD | evidence gap | HOLD | RECORDED_HOLD |

`HOLD` may not silently revoke a live lease. The operator must wait for expiry or record the appropriate provider outcome.

## Acceptance criteria

The app is acceptable for business-use rehearsal only if:

1. simultaneous clients racing the same normalized key cannot both receive a live lease;
2. server/database time, not browser time, controls lease expiry;
3. lease acquisition is atomic at the persistence layer;
4. the exact collision identity is normalized consistently server-side;
5. provider outcome recording verifies the current holder and live lease;
6. a provider SENT creates a hard fence;
7. a provider BOUNCE is displayed as route failure, never human rejection;
8. a human reopen requires a nonempty, unique retained evidence id;
9. event ids and provider/human evidence ids are unique;
10. all transitions produce immutable receipts with prior/new state and digest;
11. the UI cannot perform external sends;
12. demo data is visibly synthetic;
13. dashboard metrics are derived from stored receipts, not typed-in totals;
14. all external authority booleans remain false in exports;
15. concurrent browser tabs are covered by an actual race test, not only sequential clicks.

## Concurrency implementation requirement

Do not implement "check then insert" in two application calls.

Preferred database pattern:
- table `lanes` keyed by `collision_key`;
- transaction or compare-and-swap update that succeeds only if:
  - row absent/CLEAR, or
  - lease expired, or
  - state HUMAN_EVENT_REOPEN;
- unique event id / provider receipt / human evidence constraints;
- transition receipt inserted in the same transaction as state mutation.

If Emergent chooses PostgreSQL/Supabase, use a transactional RPC or row lock / conditional `UPDATE ... WHERE` plus unique constraints. If it chooses another persistence layer, preserve equivalent atomicity.

## Privacy boundary

Public demo uses synthetic organizations and `.invalid` domains only. Real business-use evidence may record internal receipt identifiers and aggregate counts, but public contest materials must not expose private buyer content without separate clearance.

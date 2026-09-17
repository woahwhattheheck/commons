# OneWriter product specification

Status: `SOURCE_CONTRACT / DRAFT_NOT_SUBMITTED`

## Purpose

OneWriter is an internal single-writer coordination desk for teams with several workers acting on the same external opportunity. It turns a proposed action into a collision-safe lease before any external system is used. The app itself has no external-send action.

The collision identity remains:

`organization × domain × route × purpose × opportunity`

States remain `CLEAR`, `LEASED`, `HARD_DNR`, `DEAD_ROUTE`, `HUMAN_EVENT_REOPEN`, and `HOLD`.

## Users and screens

Workers request leases from the Claim Desk. Coordinators inspect Live Lanes. Evidence reviewers record retained provider or human outcomes. The Receipt Inspector shows immutable transition receipts. The Impact view computes only from retained events and keeps Synthetic Demo data visibly separate from Measured Business Use.

A claim contains organization, domain, route, purpose, opportunity, actor, lease duration, and reason. The server normalizes the collision identity, derives the key, and returns a typed grant or denial. The UI never exposes an external-send control.

## Retained evidence identifier contract

`provider_receipt` and `human_evidence_id` are opaque retained-evidence identifiers, not notes. An admissible identifier is **exact trimmed, nonempty text of 1–240 characters with no ASCII control characters**.

The application must reject, rather than silently normalize:
- empty or whitespace-only identifiers;
- identifiers with leading or trailing whitespace;
- identifiers longer than 240 characters;
- identifiers containing ASCII control characters.

Uniqueness applies to the exact admitted identifier across the workspace. Mere string truthiness is never sufficient evidence admission.

## State transitions

| From | Event | Guard | To | Decision |
|---|---|---|---|---|
| CLEAR | CLAIM | valid lease | LEASED | GRANTED |
| LEASED | CLAIM | before expiry | LEASED | DENIED_ACTIVE_LEASE |
| LEASED | CLAIM | at/after expiry | LEASED | GRANTED_STALE_RECOVERY |
| LEASED | SENT | current holder; live lease; unique admitted provider receipt | HARD_DNR | RECORDED_SENT |
| LEASED | BOUNCE | current holder; live lease; unique admitted provider receipt | DEAD_ROUTE | RECORDED_DEAD_ROUTE |
| HARD_DNR | CLAIM | always | HARD_DNR | DENIED_HARD_DNR |
| DEAD_ROUTE | CLAIM | always | DEAD_ROUTE | DENIED_DEAD_ROUTE |
| HOLD | CLAIM | always | HOLD | DENIED_HOLD |
| HARD_DNR/DEAD_ROUTE/HOLD | HUMAN_EVENT | unique admitted retained human evidence id | HUMAN_EVENT_REOPEN | REOPENED_HUMAN_EVENT |
| HUMAN_EVENT_REOPEN | CLAIM | valid lease | LEASED | GRANTED_AFTER_HUMAN_EVENT |
| non-LEASED | HOLD | evidence gap | HOLD | RECORDED_HOLD |

A provider SENT event records only that a provider accepted the external action; it does not prove human interest. A bounce is route failure, not buyer rejection. A human event can reopen a fenced lane only after its retained evidence identifier passes the admission rule above. HOLD cannot revoke a live lease.

## Atomicity and persistence

Lease acquisition must be atomic in the persistence layer, never a client-side read-then-write sequence. Database/server time controls expiry. A transaction or equivalent compare-and-swap must grant only when the lane is absent/CLEAR, expired, or `HUMAN_EVENT_REOPEN`, and must commit the state mutation and receipt together.

Provider/human evidence identifiers must be validated before a transition and protected by uniqueness constraints after admission. Event identifiers are unique as well.

## Acceptance criteria

The business-use build is acceptable only if:
1. simultaneous claims on one normalized key cannot both win;
2. server/database time controls lease expiry;
3. lease acquisition is atomic;
4. normalization is server-side and deterministic;
5. SENT/BOUNCE require the current holder and a live lease;
6. SENT hard-fences the exact lane;
7. BOUNCE is represented as route failure, not human rejection;
8. provider/human evidence IDs obey the exact admission rule above, including rejection of whitespace-only values;
9. human reopen requires distinct retained admitted evidence;
10. event/provider/human identifiers are unique;
11. transitions create immutable prior/new-state receipts;
12. no UI action performs an external send;
13. synthetic demo data is visibly synthetic;
14. metrics derive from receipts, not manually entered totals;
15. external authority remains false in exports;
16. a real concurrent integration test proves only one racing claimant wins.

## Privacy and authority

The public demo uses synthetic organizations and `.invalid` domains. Real-use evidence may retain internal identifiers and aggregate metrics, but public materials must not expose private buyer content without separate clearance. This source contract grants no authority for provider, payment, contract, contest-submission, or revenue actions.

# Emergent master prompt — build OneWriter

Build a production-quality full-stack web app named **OneWriter**.

## Product purpose

OneWriter is an internal collision-control and evidence desk for multi-agent / multi-operator teams. It prevents two workers from contacting the same external target at nearly the same time, including when they choose different aliases or routes.

It is **not an email sender** and must not integrate any send action. External sending remains outside this app.

## Core identity and route rule

The writer-lane identity is:

**organization × domain × purpose × opportunity**

Normalize those fields server-side and derive a deterministic SHA-256 key over canonical JSON.

`route` is normalized separately and stored as **lease-scoped metadata**. Do not include route in the collision key. Two simultaneous claims for the same organization lane must collide even if one proposes `sales@...` and the other proposes `founder@...`.

Provider `SENT` / `BOUNCE` outcomes must match the normalized route selected by the current live lease.

## Visual direction

Build a polished operations console, not a generic CRM: desktop-first but excellent mobile; dense/calm/legible; nav = Claim Desk / Live Lanes / Outcomes / Receipts / Impact; strong state badges; lease countdowns; synthetic-data banner; confirmation sheet for semantic transitions; no fake charts or testimonials.

## Data model

### lanes
- `collision_key` string primary key
- `org_normalized`
- `domain_normalized`
- `purpose_normalized`
- `opportunity_normalized`
- `state`: CLEAR, LEASED, HARD_DNR, DEAD_ROUTE, HUMAN_EVENT_REOPEN, HOLD
- `holder` nullable
- `leased_route_normalized` nullable
- `lease_until` nullable server timestamp
- `last_event_id`
- `updated_at` server timestamp
- `version` integer

### events
Append-only:
- `event_id` unique
- `collision_key` foreign key
- `occurred_at` server timestamp
- kind CLAIM, SENT, BOUNCE, HUMAN_EVENT, HOLD
- actor
- `event_route_normalized`
- reason
- provider_receipt nullable unique
- human_evidence_id nullable unique
- prior_state
- decision
- new_state
- `lane_route_after`
- receipt_sha256
- external_send_authorized boolean hardcoded false

Do not store private message bodies.

## Atomicity requirement — critical

Two simultaneous clients claiming the same organization lane must never both receive a lease, even when their proposed routes differ.

Implement lease acquisition atomically in persistence. Never do client-side or two-request read-then-write.

Preferred PostgreSQL/Supabase pattern:
- transactional RPC/stored function, row lock, or equivalent conditional write keyed by collision_key;
- grant only if row is absent/CLEAR, existing lease expired, or state HUMAN_EVENT_REOPEN;
- on grant, store holder + selected normalized route + expiry in the same transaction;
- otherwise return typed denial;
- insert transition receipt atomically with the lane mutation;
- use database/server current time;
- unique constraints for event_id, provider_receipt when non-null, human_evidence_id when non-null.

If another datastore is used, preserve equivalent CAS/transaction semantics.

## Normalization

Server-side:
- org / route / purpose / opportunity: trim, collapse whitespace, consistent Unicode case-fold/lower;
- domain: parse URL-like input, reject credentials and explicit ports, lowercase host, strip `www.`, path/query/fragment, trailing dot, normalize Unicode hostname with IDNA;
- reject empty/oversized malformed values;
- display normalized writer-lane identity and proposed normalized route before claim;
- never trust a client-supplied collision key.

## Retained evidence identifier contract

`provider_receipt` and `human_evidence_id` are opaque retained-evidence identifiers, not notes. Validate them **before** any state transition. An admitted identifier is exact trimmed nonempty text of **1–240 characters**, with **no ASCII control characters, no Unicode category-C codepoints, and no non-category-C Default_Ignorable codepoints**. Reject whitespace-only, padded, overlong, control/format/private/unassigned, grapheme-joiner, Hangul-filler, variation-selector, or other Default_Ignorable-bearing values rather than silently normalizing them. Ordinary visible combining marks remain admissible. Enforce workspace-wide uniqueness after admission.

## State rules

### CLAIM
Lease duration 30–1800 seconds.
- CLEAR -> LEASED = GRANTED
- active LEASED -> LEASED = DENIED_ACTIVE_LEASE **regardless of proposed route**
- expired LEASED -> LEASED = GRANTED_STALE_RECOVERY and explicitly replace selected route
- HARD_DNR -> HARD_DNR = DENIED_HARD_DNR
- DEAD_ROUTE -> DEAD_ROUTE = DENIED_DEAD_ROUTE
- HOLD -> HOLD = DENIED_HOLD
- HUMAN_EVENT_REOPEN -> LEASED = GRANTED_AFTER_HUMAN_EVENT; select route explicitly

### SENT
Only current holder while lease is live. Requires unique admitted provider receipt **and event route equal to leased route**. Wrong-route outcome must be rejected. LEASED -> HARD_DNR = RECORDED_SENT.

SENT means provider accepted an outgoing action. It does not mean human interest, acceptance, contract, or payment.

### BOUNCE
Only current holder while lease is live. Requires unique admitted provider receipt **and event route equal to leased route**. Wrong-route outcome must be rejected. LEASED -> DEAD_ROUTE = RECORDED_DEAD_ROUTE.

Display prominently: route failure is not buyer rejection. Do not automatically open a fallback alias.

### HUMAN_EVENT
Requires unique admitted retained human evidence id. Only from HARD_DNR / DEAD_ROUTE / HOLD. -> HUMAN_EVENT_REOPEN. The next actor still must CLAIM and may intentionally select a new route.

### HOLD
Only when no live lease exists. -> HOLD. HOLD cannot silently revoke a live lease.

## Screens

### Claim Desk
Fields: org, domain, proposed route, purpose, opportunity, actor, lease seconds, reason. Preview normalized writer-lane key separately from route. Explicitly explain that changing aliases does not bypass a live lease. No Send button.

### Live Lanes
Realtime-ish list: state, holder, countdown, org/domain, selected route, purpose, opportunity, last event. Expired LEASED rows display recoverable while remaining LEASED until a new claim wins.

### Outcomes
For live leased lane: Record Provider SENT / BOUNCE; prefill or lock to currently leased route and reject tampering. For fenced lane: Record Genuine Human Event. For non-leased lane: Record HOLD.

### Receipts
Append-only explorer searchable by collision key, actor, event id, route. Raw JSON + digest. Every receipt shows `external_send_authorized:false`.

### Impact
Compute only from stored receipts: claim attempts, grants, collisions prevented, duplicate touches prevented, stale recoveries, sent hard fences, dead routes, human reopens, active fences, lease latency/duration. No manual metric entry.

## Synthetic demo

Seed the repository v2 scenario using `.invalid` domains. Walkthrough:
1. Alpha claims Northstar through ops@.
2. Beta claims the same organization lane through founder@ three seconds later and is denied.
3. Alpha records SENT on the exact leased ops@ route; lane becomes HARD_DNR.
4. A third alias is blocked.
5. Retained human evidence reopens one next action.
6. A new lease deliberately selects founder@.
7. Harbor Forge demonstrates stale recovery + matching-route BOUNCE -> DEAD_ROUTE; fallback alias remains blocked without reopen.
8. Cedar Works HOLD blocks an alternate alias until genuine human evidence.

Banner: **SYNTHETIC DEMO — these numbers are not business impact.**

## Real-use mode

Separate empty workspace named **Measured Business Use**. Never mix demo events into it. Export receipt JSON and aggregate JSON with explicit workspace/time window/event/lane counts/metrics. No private message bodies.

## Test / proof requirements

Implement tests proving:
1. true concurrent same-route claims cannot both win;
2. true concurrent **cross-route** claims for the same organization lane cannot both win;
3. normalization variants share one collision key;
4. stale recovery works and may select a new route only after expiry;
5. non-holder cannot record SENT/BOUNCE;
6. expired holder cannot record SENT/BOUNCE;
7. wrong-route SENT/BOUNCE is rejected;
8. SENT hard-fences all routes for that organization lane;
9. BOUNCE yields DEAD_ROUTE, never labels buyer rejection, and does not automatically enable fallback alias;
10. HUMAN_EVENT requires unique admitted evidence and reopens boundedly;
11. whitespace-only, padded, overlong, category-C, and Default_Ignorable-bearing provider/human evidence ids are rejected before transition, while ordinary visible combining marks remain admissible;
12. after HUMAN_EVENT_REOPEN, an explicit new route can be leased;
13. HOLD blocks claims and cannot revoke live lease;
14. provider/human evidence uniqueness;
15. server time controls expiry;
16. dashboard counts derive from receipts;
17. exported receipts always contain external_send_authorized=false;
18. demo and real-use workspaces are visibly separated;
19. credentialed/ported malformed domains are rejected.

Include at least one genuine concurrent/race integration test, not only sequential unit tests. The race test must include two different routes for one organization lane.

## Security / authority boundaries

The app must not send email/DM/forms, expose provider credentials, create provider/payment actions, claim contract/signature/payment/cash/revenue authority, submit the contest entry, or represent synthetic counts as actual business outcomes.

## Final build output requested from Emergent

When finished:
1. deploy the app;
2. provide deployed URL;
3. provide build summary;
4. provide test results, especially the cross-route concurrent race and evidence-ID rejection cases;
5. provide screenshots/walkthrough of seeded demo;
6. state whether any paid plan/upgrade was required;
7. **do not submit the contest entry**.

The human/operator will separately use the app in business, gather measured evidence, and handle contest submission.

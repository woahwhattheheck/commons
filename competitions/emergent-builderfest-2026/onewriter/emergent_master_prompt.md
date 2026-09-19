# Emergent master prompt — build OneWriter

Build a production-quality full-stack web app named **OneWriter**.

## Product purpose

OneWriter is an internal collision-control and evidence desk for multi-agent / multi-operator teams. It prevents two workers from contacting the same external target at nearly the same time, including when they choose different aliases or routes.

It is **not an email sender** and must not integrate any send action. External sending remains outside this app.

## Core identity and route rule

The writer-lane identity is **organization × domain × purpose × opportunity**. Normalize those fields server-side and derive a deterministic SHA-256 key over canonical JSON.

`route` is normalized separately and stored as lease-scoped metadata. Do not include route in the collision key. Two simultaneous claims for the same organization lane must collide even if one proposes `sales@...` and the other proposes `founder@...`.

Provider `SENT` / `BOUNCE` outcomes must match the normalized route selected by the current live lease.

A genuine `HUMAN_EVENT` may reopen a fenced lane for **one bounded next lease only**. Persist the exact prior fence (`HARD_DNR`, `DEAD_ROUTE`, or `HOLD`) and prior route with that authorization. If the human-authorized lease expires unused, restore that prior fence atomically before any later transition. Never treat that expired lease as ordinary stale-recovery authority; another genuine human event is required to reopen again.

## Visual direction

Build a polished operations console, not a generic CRM: desktop-first but excellent mobile; dense/calm/legible; nav = Claim Desk / Live Lanes / Outcomes / Receipts / Impact; strong state badges; lease countdowns; synthetic-data banner; confirmation sheet for semantic transitions; no fake charts or testimonials.

## Data model

### lanes
- `collision_key` string primary key
- normalized org/domain/purpose/opportunity
- `state`: CLEAR, LEASED, HARD_DNR, DEAD_ROUTE, HUMAN_EVENT_REOPEN, HOLD
- `holder` nullable
- `leased_route_normalized` nullable
- `lease_until` nullable server timestamp
- `reopen_from_state` nullable fenced state
- `reopen_from_route` nullable
- `last_event_id`
- `updated_at` server timestamp
- `version` integer

### workspace_identifiers
Use one workspace-wide uniqueness registry (or an equivalent database uniqueness design) shared by:
- event ids;
- provider receipt ids;
- human evidence ids.

All three identifier classes use the same admission validator before reservation: exact trimmed nonempty text of 1–240 characters; no ASCII controls; no Unicode category-C codepoints; no non-category-C Default_Ignorable codepoints; and at least one visible base codepoint outside Unicode C/M/Z categories. Reject whitespace-only, padded, overlong, control/format/private/unassigned, grapheme-joiner, Hangul-filler, variation-selector, other Default_Ignorable-bearing, or combining-mark-only values. Do not silently trim or normalize admitted identifiers. Ordinary combining marks are allowed when attached to a visible base.

Cross-type reuse is forbidden. An id used as a provider receipt cannot later be human evidence or an event id, and vice versa.

### events
Append-only:
- `event_id` unique in the workspace identifier namespace
- `collision_key` foreign key
- `occurred_at` server timestamp
- kind CLAIM, SENT, BOUNCE, HUMAN_EVENT, HOLD
- actor
- `event_route_normalized`
- reason
- provider_receipt nullable, unique in the same workspace namespace
- human_evidence_id nullable, unique in the same workspace namespace
- lease_seconds nullable
- prior_state
- decision
- new_state
- `lane_route_after`
- `reopen_expiry_refenced` boolean
- canonical normalized accepted-event JSON
- accepted-event SHA-256
- receipt SHA-256
- external_send_authorized boolean hardcoded false

The receipt SHA-256 must cover the canonical accepted-event object plus transition semantics. The accepted-event object must bind exact event id/time/kind/actor, normalized organization-lane identity, collision key, normalized event route, lease seconds, provider receipt, human evidence id, and reason. Changing any authority-bearing cause must change the receipt.

Do not store private message bodies.

## Atomicity requirement — critical

Two simultaneous clients claiming the same organization lane must never both receive a lease, even when their proposed routes differ.

Implement lease acquisition atomically in persistence. Never do client-side or two-request read-then-write.

Preferred PostgreSQL/Supabase pattern:
- transactional RPC/stored function, row lock, or equivalent conditional write keyed by collision_key;
- ordinary grant only if row is absent/CLEAR or an **ordinary** existing lease expired;
- HUMAN_EVENT_REOPEN grants exactly one lease while retaining `reopen_from_state` + `reopen_from_route`;
- before processing any later event, if a human-reopen lease is expired, atomically restore the retained prior fence and clear lease/reopen metadata; it is not generic stale recovery;
- on grant, store holder + selected normalized route + expiry in the same transaction;
- otherwise return typed denial;
- validate and reserve event/evidence ids in one shared uniqueness namespace before mutation;
- insert transition receipt atomically with the lane mutation;
- use database/server current time.

If another datastore is used, preserve equivalent CAS/transaction semantics.

## Normalization and retained identifiers

Server-side:
- org / route / purpose / opportunity: trim, collapse whitespace, consistent Unicode case-fold/lower;
- domain: parse URL-like input, reject credentials and explicit ports, lowercase host, strip `www.`, path/query/fragment, trailing dot, normalize Unicode hostname with IDNA;
- reject empty/oversized malformed values;
- display normalized writer-lane identity and proposed normalized route before claim;
- never trust a client-supplied collision key.

Event ids, `provider_receipt`, and `human_evidence_id` are opaque workspace identifiers, not notes. Before any state transition, apply the exact shared validator above. In particular, reject U+200B ZERO WIDTH SPACE; U+034F COMBINING GRAPHEME JOINER; U+FE0F VARIATION SELECTOR-16; U+115F HANGUL CHOSEONG FILLER; and combining-mark-only U+0301. Admit a value such as `provider-cafe\u0301-001` because the combining mark is attached to visible base text. Do not use language truthiness as the identifier gate. Enforce the shared namespace only after successful admission.

## State rules

### CLAIM
Lease duration 30–1800 seconds.
- CLEAR -> LEASED = GRANTED
- active LEASED -> LEASED = DENIED_ACTIVE_LEASE regardless of proposed route
- expired **ordinary** LEASED -> LEASED = GRANTED_STALE_RECOVERY and explicitly replace selected route
- HARD_DNR -> HARD_DNR = DENIED_HARD_DNR
- DEAD_ROUTE -> DEAD_ROUTE = DENIED_DEAD_ROUTE
- HOLD -> HOLD = DENIED_HOLD
- HUMAN_EVENT_REOPEN -> LEASED = GRANTED_AFTER_HUMAN_EVENT; select route explicitly while retaining prior-fence provenance
- expired LEASED that came from HUMAN_EVENT_REOPEN -> restore exact prior fence first; do not stale-recover

### SENT
Only current holder while lease is live. Requires unique admitted provider receipt and event route equal to leased route. Wrong-route outcome must be rejected. LEASED -> HARD_DNR = RECORDED_SENT. Clear any retained human-reopen provenance because the new SENT outcome establishes a new fence.

SENT means provider accepted an outgoing action. It does not mean human interest, acceptance, contract, or payment.

### BOUNCE
Only current holder while lease is live. Requires unique admitted provider receipt and event route equal to leased route. Wrong-route outcome must be rejected. LEASED -> DEAD_ROUTE = RECORDED_DEAD_ROUTE. Clear any retained human-reopen provenance because the new provider outcome establishes a new fence.

Display prominently: route failure is not buyer rejection. Do not automatically open a fallback alias.

### HUMAN_EVENT
Requires unique admitted retained human evidence id. Only from HARD_DNR / DEAD_ROUTE / HOLD. -> HUMAN_EVENT_REOPEN. Persist the exact prior fence and route. The next actor still must CLAIM and may intentionally select a new route. One human evidence event may authorize at most that one lease attempt.

### HOLD
Only when no live lease exists. -> HOLD. HOLD cannot silently revoke a live lease.

## Screens

### Claim Desk
Fields: org, domain, proposed route, purpose, opportunity, actor, lease seconds, reason. Preview normalized writer-lane key separately from route. Explicitly explain that changing aliases does not bypass a live lease. No Send button.

### Live Lanes
Realtime-ish list: state, holder, countdown, org/domain, selected route, purpose, opportunity, last event. Ordinary expired LEASED rows display recoverable. Human-reopen leases display **one-shot human authorization** and their retained prior fence; once expired they display the restored fence, never stale-recoverable.

### Outcomes
For live leased lane: Record Provider SENT / BOUNCE; prefill or lock to currently leased route and reject tampering. For fenced lane: Record Genuine Human Event. For non-leased lane: Record HOLD.

### Receipts
Append-only explorer searchable by collision key, actor, event id, route. Raw JSON + digest. Show the canonical accepted-event object/hash and transition receipt hash. Every receipt shows `external_send_authorized:false`.

### Impact
Compute only from stored receipts: claim attempts, grants, collisions prevented, duplicate touches prevented, ordinary stale recoveries, sent hard fences, dead routes, human reopens, active fences, lease latency/duration. No manual metric entry.

## Synthetic demo

Seed the repository scenario using `.invalid` domains. Walkthrough:
1. Alpha claims Northstar through ops@.
2. Beta claims the same organization lane through founder@ three seconds later and is denied.
3. Alpha records SENT on the exact leased ops@ route; lane becomes HARD_DNR.
4. A third alias is blocked.
5. Retained human evidence reopens one bounded next action.
6. A new lease deliberately selects founder@.
7. Harbor Forge demonstrates **ordinary** stale recovery + matching-route BOUNCE -> DEAD_ROUTE; fallback alias remains blocked without reopen.
8. Cedar Works HOLD blocks an alternate alias until genuine human evidence.

Banner: **SYNTHETIC DEMO — these numbers are not business impact.**

## Test / proof requirements

Implement tests proving:
1. true concurrent same-route and cross-route claims cannot both win;
2. normalization variants share one collision key;
3. ordinary stale recovery works after expiry;
4. a human-reopen lease that expires unused restores its exact prior fence and cannot stale-recover without a new human event;
5. non-holder, expired-holder, and wrong-route SENT/BOUNCE are rejected;
6. SENT hard-fences all routes; BOUNCE is route failure and does not enable fallback;
7. HUMAN_EVENT requires unique admitted evidence and reopens only one bounded lease attempt;
8. event/provider/human ids reject whitespace-only, padded, overlong, ASCII-control, category-C, Default_Ignorable-bearing, and combining-mark-only values before transition; the deployed-app proof matrix must include U+200B, U+034F, U+FE0F, U+115F, and combining-only U+0301 rejection plus a visible-base+combining positive;
9. event/provider/human identifiers share one workspace namespace; provider->human, human->provider, and event<->evidence reuse fail;
10. changing admitted provider/human evidence, lease seconds, reason, identity, route, actor, kind, or timestamp changes the transition receipt digest;
11. HOLD blocks claims and cannot revoke live lease;
12. server time controls expiry;
13. dashboard counts derive from receipts;
14. exported receipts always contain external_send_authorized=false;
15. demo and real-use workspaces are visibly separated;
16. credentialed/ported malformed domains are rejected.

Run the complete hostile suite under normal Python and real `python -O`. Include at least one genuine concurrent/race integration test in the deployed app, including two different routes for one organization lane.

## Security / authority boundaries

The app must not send email/DM/forms, expose provider credentials, create provider/payment actions, claim contract/signature/payment/cash/revenue authority, submit the contest entry, or represent synthetic counts as actual business outcomes.

## Final build output requested from Emergent

When finished:
1. deploy the app;
2. provide deployed URL;
3. provide build summary;
4. provide test results, especially cross-route race, bounded human-reopen expiry, strict Unicode identifier admission across event/provider/human ids, cross-type identifier rejection, and receipt-causation cases;
5. provide screenshots/walkthrough of seeded demo;
6. state whether any paid plan/upgrade was required;
7. **do not submit the contest entry**.

The human/operator will separately use the app in business, gather measured evidence, and handle contest submission.
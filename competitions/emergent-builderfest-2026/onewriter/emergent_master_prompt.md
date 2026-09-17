# Emergent master prompt — build OneWriter

Build a production-quality full-stack web app named **OneWriter**.

## Purpose

OneWriter is an internal collision-control and evidence desk for multi-agent / multi-operator teams. It prevents two workers from independently taking the same externally directed action at nearly the same time.

It is **not** an email, DM, or form sender and must not integrate an external-send action. External execution remains outside this app.

The lane identity is:

**organization × domain × route × purpose × opportunity**

Normalize those fields server-side and derive a deterministic SHA-256 collision key over canonical JSON. Never trust a client-supplied collision key.

## Required states and events

States:
- CLEAR
- LEASED
- HARD_DNR
- DEAD_ROUTE
- HUMAN_EVENT_REOPEN
- HOLD

Events:
- CLAIM
- SENT
- BOUNCE
- HUMAN_EVENT
- HOLD

Every transition creates an immutable receipt containing event id, collision key, server timestamp, actor, prior state, decision, new state, digest, and `external_send_authorized=false`.

## Data model

### lanes
- collision_key primary key
- normalized org/domain/route/purpose/opportunity
- state
- holder nullable
- lease_until nullable server timestamp
- last_event_id
- updated_at server timestamp
- version integer

### events
Append-only.
- event_id unique
- collision_key foreign key
- occurred_at server timestamp
- kind
- actor
- reason
- provider_receipt nullable unique
- human_evidence_id nullable unique
- prior_state
- decision
- new_state
- receipt_sha256
- external_send_authorized hardcoded false

Do not store private message bodies.

## Retained evidence identifier contract — security critical

`provider_receipt` and `human_evidence_id` are opaque retained-evidence identifiers, not notes. Validate them **before** any state transition.

An admitted identifier must be exact trimmed, nonempty text of **1–240 characters** with **no ASCII control characters**. Reject rather than silently normalize:
- empty or whitespace-only values;
- leading or trailing whitespace;
- values over 240 characters;
- ASCII control characters.

Do not use JavaScript/Python truthiness as the evidence gate. After admission, enforce workspace-wide uniqueness for non-null provider and human evidence identifiers.

## Atomic lease requirement — critical

Two simultaneous browser clients claiming one collision key must never both receive a live lease.

Lease acquisition must be atomic in the persistence layer. Do not implement a client-side or multi-request read-then-write check.

Preferred PostgreSQL/Supabase pattern:
- transaction / RPC / stored function or equivalent conditional write;
- keyed by collision_key;
- grant only if row is absent/CLEAR, current lease is expired, or state is HUMAN_EVENT_REOPEN;
- otherwise return a typed denial;
- update lane and insert transition receipt in the same transaction;
- use database/server current time for expiry;
- enforce unique event id and admitted provider/human evidence identifiers.

If another datastore is used, preserve equivalent compare-and-swap / transactional behavior.

## Normalization

Server-side:
- org / route / purpose / opportunity: trim, collapse whitespace, case-fold consistently;
- domain: lowercase, remove scheme, strip `www.`, path, and trailing dot;
- reject empty, oversized, malformed values;
- display the normalized identity before claim.

## State rules

### CLAIM
Lease duration 30–1800 seconds.
- CLEAR -> LEASED = GRANTED
- active LEASED -> LEASED = DENIED_ACTIVE_LEASE
- expired LEASED -> LEASED = GRANTED_STALE_RECOVERY
- HARD_DNR -> HARD_DNR = DENIED_HARD_DNR
- DEAD_ROUTE -> DEAD_ROUTE = DENIED_DEAD_ROUTE
- HOLD -> HOLD = DENIED_HOLD
- HUMAN_EVENT_REOPEN -> LEASED = GRANTED_AFTER_HUMAN_EVENT

### SENT
Only the current holder while the lease is live may record it. Requires a unique **admitted** provider receipt identifier. LEASED -> HARD_DNR = RECORDED_SENT.

SENT means only that a provider accepted an outgoing action. It does not prove that a human read, replied, accepted, contracted, or paid.

### BOUNCE
Only the current holder while the lease is live may record it. Requires a unique **admitted** provider receipt identifier. LEASED -> DEAD_ROUTE = RECORDED_DEAD_ROUTE.

Display prominently: route failure is not buyer rejection.

### HUMAN_EVENT
Requires a unique **admitted** retained human evidence identifier. Only from HARD_DNR / DEAD_ROUTE / HOLD. -> HUMAN_EVENT_REOPEN = REOPENED_HUMAN_EVENT.

Whitespace-only or padded identifiers must fail before the lane can reopen. The next actor must still CLAIM.

### HOLD
Allowed only when no live lease exists. -> HOLD = RECORDED_HOLD. HOLD cannot silently revoke a live lease.

## Screens

### Claim Desk
Form: org, domain, route, purpose, opportunity, actor, lease seconds, reason. Preview normalized identity and collision key. Show typed grant/denial with receipt digest. No Send button.

### Live Lanes
Show state, holder, lease countdown, normalized identity, last event, and next admissible action. Filters for leased, recoverable, DNR, dead route, human reopen, and hold. Expired LEASED rows may display as recoverable but remain LEASED until a new claim wins.

### Outcomes
For a live leased lane, allow recording Provider SENT or Provider BOUNCE using the exact retained-evidence admission rule above. For a fenced lane, allow Genuine Human Event using the same strict admission rule. For a non-leased lane, allow HOLD. Explain every semantic distinction in the UI.

### Receipts
Append-only explorer searchable by collision key, actor, and event id. Expand raw JSON, copy digest, and visibly show `external_send_authorized=false`.

### Impact
Compute only from stored receipts: claim attempts, grants, collisions prevented, duplicate touches prevented, stale recoveries, sent hard fences, dead routes, human reopens, active DNR/dead-route counts, and median lease duration. Do not allow manual metric entry.

## Workspaces and synthetic demo

Seed the repository synthetic scenario using `.invalid` organizations. Clearly banner:

**SYNTHETIC DEMO — these numbers are not business impact.**

Keep a separate empty workspace named **Measured Business Use**. Never silently mix demo events into it.

Demo walkthrough:
1. Alpha gets a lease.
2. Beta races the same lane and is denied.
3. SENT hard-fences the lane.
4. Another claim is blocked.
5. Genuine retained human evidence reopens one next action.
6. A different lease expires and is recovered.
7. BOUNCE becomes DEAD_ROUTE.
8. HOLD blocks a claim until admitted human evidence arrives.

Allow export of receipt JSON and aggregate JSON with workspace, start/end timestamps, event/lane counts, and metrics. Do not export private message bodies.

## Required tests

Prove at least:
1. two truly simultaneous claims on one normalized key cannot both win;
2. normalization variants collide;
3. stale lease recovery works;
4. non-holder cannot record SENT/BOUNCE;
5. expired holder cannot record SENT/BOUNCE;
6. SENT hard-fences claims;
7. BOUNCE yields DEAD_ROUTE, never human rejection;
8. HUMAN_EVENT reopens only with unique admitted evidence;
9. whitespace-only, padded, overlong, and control-character provider/human evidence identifiers are rejected before transition;
10. provider and human evidence uniqueness;
11. HOLD blocks claims and cannot revoke a live lease;
12. server time controls expiry;
13. dashboard counts derive from receipts;
14. exported receipts always contain `external_send_authorized=false`;
15. demo and measured-business workspaces remain separated.

Include at least one genuine concurrent persistence-layer race integration test, not only sequential unit tests or browser clicks.

## Authority boundaries

The app must not:
- perform an external send;
- expose provider credentials;
- create payment actions;
- claim contract/signature/payment/cash/revenue authority;
- submit the contest entry;
- represent synthetic counts as actual business outcomes.

## Final build output requested from Emergent

When finished:
1. deploy the app;
2. provide the deployed URL;
3. provide a concise build summary;
4. provide test results, especially the concurrent lease race and evidence-ID rejection cases;
5. provide screenshots or a walkthrough of the seeded demo;
6. state explicitly whether any paid plan/upgrade was required;
7. do **not** submit the contest entry.

The human/operator will separately use the app in business, gather measured evidence, and handle any contest submission.

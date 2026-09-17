# Emergent master prompt — build OneWriter

Build a production-quality full-stack web app named **OneWriter**.

## Product purpose

OneWriter is an internal collision-control and evidence desk for multi-agent / multi-operator teams. It prevents two workers from independently contacting the same external target at nearly the same time.

It is **not an email sender** and must not integrate a send action. It coordinates who is allowed to own a proposed lane. External sending remains outside this app.

The core identity is:

**organization × domain × route × purpose × opportunity**

Normalize those fields server-side and derive a deterministic SHA-256 collision key over canonical JSON.

## Visual direction

Build a polished operations console, not a generic CRM:
- desktop-first but excellent mobile;
- dense, calm, legible;
- primary nav: Claim Desk / Live Lanes / Outcomes / Receipts / Impact;
- strong state badges;
- clear countdown timers for leases;
- synthetic-data banner when demo mode is on;
- every destructive or semantic transition gets a confirmation sheet showing the prior and next state;
- do not use fake charts or placeholder testimonials.

## Data model

### lanes
- collision_key: string primary key
- org_normalized
- domain_normalized
- route_normalized
- purpose_normalized
- opportunity_normalized
- state enum: CLEAR, LEASED, HARD_DNR, DEAD_ROUTE, HUMAN_EVENT_REOPEN, HOLD
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
- kind enum: CLAIM, SENT, BOUNCE, HUMAN_EVENT, HOLD
- actor
- reason
- provider_receipt nullable unique
- human_evidence_id nullable unique
- prior_state
- decision
- new_state
- receipt_sha256
- external_send_authorized boolean hardcoded false

Do not store private message bodies.

## Atomicity requirement — critical

Two simultaneous browser clients claiming the same key must never both receive a lease.

Implement lease acquisition atomically in the persistence layer. Do not do a client-side or two-request “read then write”.

Preferred if PostgreSQL/Supabase is available:
- transaction / RPC / stored function, or an equivalent conditional write;
- keyed by collision_key;
- grant only if row is absent/CLEAR, the existing lease is expired, or state is HUMAN_EVENT_REOPEN;
- otherwise return a typed denial;
- update lane + insert receipt in the same transaction;
- use database/server current time for expiry, not browser time;
- enforce unique event_id, provider_receipt when non-null, human_evidence_id when non-null.

If you choose a different datastore, preserve equivalent compare-and-swap / transactional behavior.

## Normalization

Server-side:
- org / route / purpose / opportunity: trim, collapse whitespace, Unicode case-fold/lower consistently;
- domain: lowercase, remove URL scheme, strip `www.`, path, and trailing dot;
- reject empty/oversized malformed values;
- display the normalized collision identity before claim.

Never trust a client-supplied collision key.

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
Only the current holder, while lease is live, may record.
Requires unique provider_receipt.
LEASED -> HARD_DNR = RECORDED_SENT.

SENT means provider accepted an outgoing action. It does not mean a human read/replied, accepted anything, or paid.

### BOUNCE
Only the current holder, while lease is live, may record.
Requires unique provider_receipt.
LEASED -> DEAD_ROUTE = RECORDED_DEAD_ROUTE.

Display prominently: route failure is not buyer rejection.

### HUMAN_EVENT
Requires unique, nonempty retained human_evidence_id.
Only from HARD_DNR / DEAD_ROUTE / HOLD.
-> HUMAN_EVENT_REOPEN = REOPENED_HUMAN_EVENT.

This is a bounded reopen. The next actor still must CLAIM.

### HOLD
Only when no live lease exists.
-> HOLD = RECORDED_HOLD.
HOLD cannot silently revoke a live lease.

## Screens

### Claim Desk
Form: org, domain, route, purpose, opportunity, actor, lease seconds, reason.
Preview normalized identity and key.
Submit claim.
Show typed result with receipt digest.
Absolutely no Send button.

### Live Lanes
Realtime-ish table/cards sorted by urgency.
State, holder, lease countdown, org, route, purpose, opportunity, last event.
Filters: leased, recoverable, DNR, dead route, human reopen, hold.
Expired LEASED rows visually mark “recoverable” but remain state LEASED until a new claim wins.

### Outcomes
Select a live leased lane:
- Record Provider SENT
- Record Provider BOUNCE
For fenced lane:
- Record Genuine Human Event
For non-leased lane:
- Record HOLD
Every form explains semantics and required evidence id.

### Receipts
Append-only chronological explorer.
Search by collision key, actor, event id.
Expandable raw JSON.
Copy receipt digest.
Show `external_send_authorized: false` on every receipt.

### Impact
Compute only from stored event receipts:
- claim attempts
- claims granted
- collisions prevented
- duplicate touches prevented
- stale lanes recovered
- sent hard fences
- dead routes recorded
- human reopens
- active DNR count
- active dead-route count
- median lease duration

Never allow manual metric entry.

## Seed synthetic demo

Seed the semantic scenario from the repository `demo_events.json` logic using synthetic `.invalid` organizations only.

Provide a Reset Demo control that restores the synthetic scenario.

Banner:
**SYNTHETIC DEMO — these numbers are not business impact.**

Create a demo walkthrough mode that highlights:
1. Alpha gets the Northstar lease.
2. Beta collides three seconds later and is denied.
3. SENT hard-fences Northstar.
4. Another claim is blocked.
5. Human evidence reopens one next action.
6. Harbor Forge lease expires and is recovered.
7. Bounce becomes DEAD_ROUTE.
8. Cedar Works HOLD blocks a claim until human evidence.

## Real-use mode

Add a separate empty workspace named **Measured Business Use**. Do not silently mix demo events into it.

Make it possible to export:
- receipt JSON
- aggregate JSON with explicit workspace, start/end timestamps, event/lane counts, and metrics.

No private message bodies.

## Test / proof requirements

Implement tests proving:
1. two simultaneous claims on same normalized key cannot both win;
2. normalization variants collide;
3. stale lease recovery works;
4. non-holder cannot record SENT/BOUNCE;
5. expired holder cannot record SENT/BOUNCE;
6. SENT hard-fences claims;
7. BOUNCE yields DEAD_ROUTE and never labels rejection;
8. HUMAN_EVENT needs unique evidence and reopens boundedly;
9. HOLD blocks claims and cannot revoke live lease;
10. provider receipt and human evidence uniqueness;
11. server time controls expiry;
12. dashboard counts derive from receipts;
13. exported receipts always contain external_send_authorized=false;
14. demo and real-use workspaces are visibly separated.

Include at least one true concurrent/race integration test, not only sequential unit tests.

## Security / authority boundaries

The app must not:
- send email/DM/forms;
- expose provider credentials;
- create provider/payment actions;
- claim contract, signature, payment, cash, or revenue authority;
- submit the contest entry;
- represent synthetic counts as actual business outcomes.

Every receipt has `external_send_authorized=false`.

## Final build output requested from Emergent

When finished:
1. deploy the app;
2. provide the deployed URL;
3. provide a short build summary;
4. provide test results, especially the concurrent claim race;
5. provide screenshots or a walkthrough of the seeded demo;
6. state explicitly whether any paid plan/upgrade was required;
7. do **not** submit the contest entry.

The human/operator will separately use the app in business, gather measured evidence, and handle contest submission.

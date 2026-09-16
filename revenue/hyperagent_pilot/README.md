# Hyperagent deterministic event → Slack-transcript pilot adapter

This package is an **offline fulfillment-readiness artifact** for the paid-pilot seam recorded in Commons issue #14225. It does not contact Hyperagent or Slack, does not use credentials, and does not claim buyer acceptance, funding, payment, or revenue.

The commercial posture remains **PROPOSED / NOT ACCEPTED**. Hyperagent outreach remains **DNR until a new human event**. Building or merging this package does not alter that rule.

## Acceptance proof

`fixture_30_events.json` contains exactly 30 synthetic events: 10 `atlas`, 10 `beacon`, and 10 `cipher` events. The three backend schemas are intentionally heterogeneous.

The adapter normalizes each event into stable SHA-256 run/thread/event identities and projects the retained generation into canonical transcript artifacts. The focused contract proves:

- 30 clean fixture events produce exactly **6** logical transcript artifacts and **30** unique logical messages;
- replaying all 30 source events a second time still produces the same 30 logical messages, with 30 exact source duplicates suppressed;
- same backend/source-event ID with changed canonical semantics fails closed;
- conflicting sequence ownership inside a source run fails closed;
- two clean projections of the same fixture are byte-identical, independent of source ordering;
- `ACTION_REQUEST` generation is bound to normalized run/thread/event identity plus action text;
- action candidates require an authenticated `hyperagent-pilot/approval/v1` that binds the exact run, event, action generation, and approval window;
- missing, malformed, foreign, duplicate, wrong-run, wrong-generation, unauthenticated, noncanonical, or stale approval input produces **zero** candidate payloads;
- every transcript and candidate fixes `outbound_authorized=false`; no function sends or invokes a provider.

## Schemas

### Atlas

```json
{"backend":"atlas","run":{"id":"a-run-1","thread":"a-thread-1"},"event":{"id":"a1-e2","sequence":2,"type":"MESSAGE","text":"..."}}
```

### Beacon

```json
{"backend":"beacon","execution_id":"b-run-1","conversation_key":"b-thread-1","record":{"id":"b1-e2","index":2,"kind":"MESSAGE","body":"..."}}
```

### Cipher

```json
{"backend":"cipher","trace":{"run":"c-run-1","channel":"c-thread-1"},"item":{"key":"c1-e2","ordinal":2,"type":"MESSAGE","payload":{"text":"..."}}}
```

Unknown fields are rejected at every schema level. IDs are bounded opaque text; sequence numbers are bounded integers with bool rejected; message text is bounded and control-character checked.

## Deterministic identity and replay

Canonical identities are namespaced by backend and purpose:

- run identity: SHA-256 of backend + source run ID;
- thread identity: SHA-256 of backend + source thread key;
- event identity: SHA-256 of backend + source event ID;
- action generation: SHA-256 of normalized run/thread/event identity + action text.

An exact repeat of a source event is idempotent. Reusing the same backend/source-event ID with changed canonical semantics is a conflict, not an update. Reusing one source-run sequence for a different event is rejected.

Projection output is canonical ASCII JSON (`sort_keys=True`, compact separators, no NaN) and carries SHA-256 receipts for each artifact and the whole projection.

## Approval authority boundary

A structural approval object alone is **not authority**. Hyperagent retains human approval authority under issue #14225, so the candidate path also requires possession of a retained runtime approval key supplied outside this repository.

`hyperagent-pilot/approval/v1` has these signed fields:

```json
{
  "schema": "hyperagent-pilot/approval/v1",
  "run_id": "...",
  "event_id": "...",
  "action_generation": "...",
  "approved_at": "2026-09-16T18:00:00Z",
  "expires_at": "2026-09-16T19:00:00Z"
}
```

The issuer computes lowercase `auth_tag = HMAC-SHA256(approval_auth_key, canonical_json(signed_fields))` and appends that tag to the object. `approval_auth_key` must be 32..128 bytes and is injected at runtime; no buyer key or secret is committed here.

`prepare_candidate_payloads()`:

1. authenticates the approval with the retained runtime key using `hmac.compare_digest`;
2. requires exact run/event/action-generation binding;
3. evaluates the signed approval window against captured process UTC, with **no caller-supplied clock**;
4. fails the whole approval set closed on malformed, unauthenticated, foreign, duplicate, or stale input;
5. emits only `hyperagent-pilot/offline-slack-candidate/v1` bytes with `approval_validated=true`, an `approval_receipt_sha256`, `outbound_authorized=false`, and `provider_action_performed=false`.

The approval receipt digest binds the candidate to the exact authenticated approval generation. Possessing or validating an approval still does **not** authorize this package to send anything.

## Run the proof

From repository root:

```bash
python -m py_compile \
  revenue/hyperagent_pilot/__init__.py \
  revenue/hyperagent_pilot/adapter.py \
  revenue/hyperagent_pilot/test_adapter.py

python -m unittest -v revenue.hyperagent_pilot.test_adapter
python -O -m unittest -v revenue.hyperagent_pilot.test_adapter
```

Hosted CI is useful evidence only when it actually runs. Missing or queued is `UNKNOWN`, never green.

## Commercial handoff

What this artifact makes ready for a future human-approved paid pilot:

1. obtain a buyer-approved mapping from real event schemas to one of these bounded adapter schemas, or add a separately reviewed schema adapter;
2. validate a retained synthetic/sample generation locally;
3. agree which event classes are transcript-only versus action candidates;
4. provision the buyer-controlled approval issuer/key and approval-window semantics outside this repository;
5. only after a new human buyer event, a separately authorized integration may translate authenticated offline candidate artifacts into provider actions.

This repository artifact itself does **not** perform step 5.

## Authority ceiling

Always false / not claimed here:

- Hyperagent contact or follow-up;
- Slack send, thread creation, message mutation, credential use, or provider login;
- approval issuance or buyer acceptance;
- deployment to buyer infrastructure;
- contract execution or pricing acceptance;
- payment request, bank/Stripe action, booked revenue, or cash receipt;
- permission to override the existing DNR.

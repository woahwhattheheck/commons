# Hyperagent deterministic event → Slack-transcript pilot adapter

This package is an **offline fulfillment-readiness artifact** for the paid-pilot seam recorded in Commons issue #14225. It does not contact Hyperagent or Slack, does not use credentials, and does not claim buyer acceptance, funding, payment, or revenue.

The existing commercial posture remains **PROPOSED / NOT ACCEPTED**. Hyperagent outreach remains **DNR until a new human event**. Building or merging this package does not alter that rule.

## Acceptance proof

`fixture_30_events.json` contains exactly 30 synthetic events: 10 `atlas`, 10 `beacon`, and 10 `cipher` events. The three backend schemas are intentionally heterogeneous.

The adapter normalizes each event into stable SHA-256 run/thread/event identities and then projects the retained generation into canonical transcript artifacts. The focused test contract proves:

- 30 clean fixture events produce exactly **6** logical transcript artifacts and **30** unique logical messages;
- replaying all 30 source events a second time still produces the same 30 logical messages, with 30 exact source duplicates suppressed;
- same backend/source-event ID with changed semantics fails closed;
- conflicting sequence ownership inside a source run fails closed;
- two clean projections of the same fixture are byte-identical, and source ordering does not change projection bytes;
- `ACTION_REQUEST` events can produce an **offline candidate payload** only when an approval binds the exact normalized `run_id`, `event_id`, and `action_generation` and is current at caller-supplied canonical UTC;
- missing, malformed, foreign, duplicate, wrong-run, wrong-generation, noncanonical-time, or stale approval input produces **zero** candidate payloads;
- every transcript and candidate payload fixes `outbound_authorized=false`; no function sends or invokes a provider.

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

Provider IDs are never treated as globally unique by themselves. Canonical IDs are namespaced by backend and purpose:

- run identity: SHA-256 of backend + source run ID;
- thread identity: SHA-256 of backend + source thread key;
- event identity: SHA-256 of backend + source event ID;
- action generation: SHA-256 of the normalized run/thread/event identity + action text.

An exact repeat of a source event is idempotent. Reusing the same `(backend, source_event_id)` with changed canonical semantics is a conflict, not an update. Reusing one source-run sequence for a different event is also rejected.

Projection output is canonical ASCII JSON (`sort_keys=True`, compact separators, no NaN) and carries SHA-256 receipts for each artifact and the whole projection.

## Approval boundary

`prepare_candidate_payloads()` accepts only `hyperagent-pilot/approval/v1` objects containing exact `run_id`, `event_id`, `action_generation`, `approved_at`, and `expires_at` bindings. Times are canonical second-precision UTC ending in `Z`.

Even a valid approval produces only `hyperagent-pilot/offline-slack-candidate/v1` bytes. Those bytes explicitly state:

- `approval_validated=true`;
- `outbound_authorized=false`;
- `provider_action_performed=false`.

This is an evidence/compiler boundary, not a Slack client. There is no token, webhook, HTTP, socket, subprocess, browser, or provider SDK in the package.

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

Hosted CI is useful evidence only when it actually runs. A missing/queued run is `UNKNOWN`, never green.

## Commercial handoff

What this artifact makes ready for a future human-approved paid pilot:

1. obtain a buyer-approved mapping from their real event schemas to one of these bounded adapter schemas (or add a separately reviewed schema adapter);
2. validate a retained synthetic/sample generation locally;
3. agree which event classes are transcript-only versus action candidates;
4. obtain the buyer's actual approval-generation and expiry semantics;
5. only after a new human buyer event, a separately authorized integration may translate offline candidate artifacts into provider actions.

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

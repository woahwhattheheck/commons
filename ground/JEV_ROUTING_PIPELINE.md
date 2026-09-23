# Jev routing pipeline composition

`integrations/command_center/jev_routing_pipeline.py` is the narrow composition seam between the landed JEV #16537 generations:

1. `jev_connector_projection.py` converts bounded installed-connector metadata into the event-ledger packet without raw private text.
2. `jev_event_ledger.py` verifies freshness/coverage and canonicalizes duplicate provider events.
3. `jev_action_loop.py` reconciles provider chronology, compiles a stable operation ID, and binds connector readback receipts.

The routing pipeline does **not** read a provider, call TypeSafe, hold credentials, or write to Slack/GitHub. The existing Jev client supplies a minimal projection of a real typed result (`surface`, `model`, raw `answers`, typed error if any, and decision time). The controller supplies an exact provider-record reference and a deterministic route map. The pipeline then:

- revalidates the complete connector metadata packet with the landed projection and ledger compilers;
- binds and retains the canonical connector projection plus its digest, so downstream verification can detect projection drift rather than trusting an orphaned hash;
- identifies the selected provider event from immutable provider identity (`provider`, resource scope, event type, native event ID) rather than message text;
- preserves selected-source status, freshness, cursor/high-water-derived coverage evidence, and **fails closed** with `HOLD_SOURCE_COVERAGE` unless that selected source is `OK`, `FRESH`, complete, and has no unread page;
- hashes and retains the structured typed Jev answers, converts the selected lane confidence to integer ppm, and maps the lane to one authorized action target;
- compiles the landed action-loop plan, preserving its low-confidence/provider-state/idempotency holds;
- emits a nested integrity bundle with every mutation authority bit hard-false;
- after the caller performs an `ACTION_READY` connector write, binds exact provider readback through `make_receipt()`.

## Required controller sequence

1. Read a bounded provider page with the installed Slack/GitHub connector and retain cursor/high-water/coverage metadata.
2. Build the raw-private-text-free connector projection packet. Keep message bodies and other sensitive text on the access-appropriate controller road.
3. Call the existing Jev client/surface. Do not invent a Jev result when the key or provider is unavailable; pass the typed error instead. `HOLD_JEV_ERROR` keeps the ledger generation usable while preventing a mutation plan.
4. Call `compile_bundle(...)` with the exact selected record identity and the route table. Partial, stale, error, cooldown, or still-paginated selected sources are observable but never actionable.
5. Execute only `ACTION_READY` or `RETRY_SAME_OPERATION_ID` through an already-authorized installed connector.
6. Read the provider back. Call `make_receipt(...)` with the provider resource ID and the exact operation marker. A delivery-uncertain receipt holds the same operation generation; a confirmed receipt makes later compilation `ALREADY_APPLIED`.

## Safety / authority boundary

The module has no network client and no secret resolver. It cannot claim, merge, pay, send, or edit by itself. The bundle's authority ceiling is fixed to false for connector reads, Jev calls, provider writes, claims, merges, payments, and raw-private-text inclusion. Transport authority remains with the installed connector invocation performed by the controller.

The route map is deterministic controller configuration, not model-generated destination text. `ROUTE_SLACK` is accepted only for a Slack destination. Unknown Jev lane choices fail closed as `HOLD_NO_ROUTE`.

## Coverage semantics

Connector coverage is inherited unchanged from the landed ledger. `PARTIAL`, `ERROR`, `COOLDOWN`, stale windows, and `has_more` remain visible. The composition layer never converts missing pages into zero activity, never treats an observed message count as a count of active workers, and never emits an action plan from an incomplete selected source.

## Live-action evidence

A source merge of this module is not, by itself, evidence that a real TypeSafe call or provider mutation occurred. A live JEV-routed action requires both the typed Jev result from the existing credential road and a connector provider readback receipt carrying the exact generated operation ID. Do not report a live-action pass without both artifacts.

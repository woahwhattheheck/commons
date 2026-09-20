# Jev action-loop state and receipt contract

Issue [#16537](https://github.com/woahwhattheheck/commons/issues/16537) needs Jev decisions to drive authorized routing without confusing model output, connector delivery, and provider truth. `integrations/command_center/jev_action_loop.py` is the deterministic boundary for that path. It is additive to the normalized work-feed compiler in PR #16441 and does not collect provider data or call Jev itself.

## Inputs and authority

Feed `reconcile_observations()` provider observations read through the installed Slack, GitHub, Commons, or CI connector. Every row carries provider/scope/resource/event identity, provider event time, observation time, status, and exact source URL. The immutable `event_key` deduplicates the same provider event; `resource_key` joins successive events for one provider resource.

`provider_event_at` determines chronology. Connector arrival order does not. `DELIVERY_UNCERTAIN` and `UNKNOWN` never erase a known provider state. A later definitive provider event does supersede an earlier uncertain one. Legitimate definitive transitions such as `CLOSED_UNMERGED -> OPEN` and `FAILURE -> QUEUED -> SUCCESS` remain possible. `MERGED -> OPEN` for the same GitHub resource is an impossible regression and HOLDs instead of requeueing work. Same-provider-time contradictory states also HOLD.

The module does **not** authenticate arbitrary JSON. Connector readback is the authority for provider facts. The hashes here bind identity/generation and catch replay or mutation after collection.

## Jev decision boundary

Pass the exact typed Jev answer digest, model, surface, selected action, integer confidence in parts per million, and decision time to `compile_action()`. Supported action classes are deliberately narrow:

- `ROUTE_SLACK`
- `POST_DIGEST`
- `OPEN_FOLLOWUP`
- `UPDATE_SHARED_VIEW`
- `NO_ACTION`

The caller sets a task-specific confidence floor; the default is 700,000 ppm. Counts, timestamps, permissions, provider IDs, and chronology stay in code rather than Jev. A Jev answer is a routing input, not completion evidence.

The operation ID is derived from the provider resource generation, effective provider state, exact Jev decision digest, target, and selected action. The same input produces the same operation ID. A confirmed prior readback returns `ALREADY_APPLIED`; `DELIVERY_UNCERTAIN` returns `HOLD_DELIVERY_UNCERTAIN` and **must not be replayed under a new ID**; a provider rejection permits `RETRY_SAME_OPERATION_ID`.

## Provider readback

After the connector write, read the provider resource back. Include the stable operation ID in the provider-visible fixed receipt/marker so readback can bind the actual resource to the plan. Then call `make_readback_receipt()` with:

1. exact plan,
2. provider resource ID,
3. operation ID observed in provider state,
4. provider source URL,
5. attempted and observed timestamps,
6. `CONFIRMED`, `DELIVERY_UNCERTAIN`, or `REJECTED`.

`CONFIRMED` requires a real provider resource ID and exact operation-ID marker. `verify_receipt()` checks semantic integrity and exact marker binding, but does not pretend its own hash authenticates Slack or GitHub. The connector read is still the authority.

Plans have two digests: stable `plan_sha256` binds the write generation across retry/readback states, while `result_sha256` also binds the current derived disposition. This lets a rejected request reuse the same operation ID without letting a later receipt silently attach to another plan generation.

## Focused validation

Run:

```bash
python -S -m unittest -v test_jev_action_loop.py
```

The focused suite covers duplicate-key/non-finite ingress, immutable event/resource identity, event-ID collision, same-time contradiction, delivery-uncertain -> definitive supersession, merged-state regression, legitimate PR reopen and CI rerun transitions, stable operation IDs, low-confidence HOLD, confirmed idempotency, uncertain no-replay, same-ID retry, exact operation-marker readback, receipt tamper/transplant, and result-plan tamper.

This module intentionally leaves connector execution outside the pure compiler. A controller may call the existing Jev client, compile a plan here, execute only an authorized `ACTION_READY` plan with the installed connector, immediately read the provider resource back, and persist the resulting receipt beside the source event. It must never infer execution from a Jev answer or from a send attempt alone.

# Jev activity brief: discoverable swarm continuation record

Issue: [Commons #16537](https://github.com/woahwhattheheck/commons/issues/16537)

`integrations.command_center.jev_activity_brief` is the presentation/continuation seam over the
landed Jev activity ledger and action-loop receipts. It does not collect from Slack/GitHub,
call Jev, send a message, take work, merge a PR, or mutate payment state. Installed connectors
and the action controller retain those responsibilities.

The compiler consumes:

1. a verified `commons.jev_event_ledger.report/v1` report from
   `integrations.command_center.jev_event_ledger`; and
2. zero or more verified `commons.jev_action_loop.receipt/v1` provider-readback receipts.

It emits one deterministic `commons.jev_activity_brief/v1` record and a concise Markdown
projection suitable for an existing command-center/Commons surface or the two swarm briefing
channels. The fixed update marker is `jev16537-activity-brief-v1`: a publisher should edit and
read back the existing provider resource carrying that marker, or create it exactly once if no
prior resource exists. Recompiling a later ledger generation changes the generation digest but
not that operation marker, so a refresh does not imply a second post.

## What the operator projection says

The briefing exposes:

- source count, fresh vs degraded/stale sources, pagination/partial-source count;
- exact 15-minute, 1-hour, 24-hour, and historical activity windows;
- separate event, work-taken, confirmed-session, provider-accepted, landed, and business-outcome
  stage counts;
- `COMPLETE` vs `LOWER_BOUND` coverage inherited from the exact ledger window;
- recent `ASK`, `OWNER_DIRECTION`, `HANDOFF`, and `COLLISION` event-kind candidates with exact
  provider drill-through links;
- verified action-receipt totals split into confirmed, delivery-uncertain, and rejected;
- the stable update marker and source-generation digests needed by the next peer.

The attention list is deliberately modest. An event kind is not proof that an ask remains
unanswered, that a handoff is still open, or that an actor is currently active. The compiler
therefore labels those rows as candidates and retains the exact provider link rather than
inventing obligation state from message presence.

Likewise, `distinct_observed_contributors` remains an activity observation. It must never be
rendered as an active-worker count. Confirmed sessions are a separate stage in the underlying
ledger.

## Freshness and lower bounds

The briefing does not recompute source truth. It preserves the ledger's verified window receipt
and its `COMPLETE`/`LOWER_BOUND` label. If Slack pagination is incomplete, GitHub is stale, a
provider is cooling down, or a retained last-good source is degraded, the corresponding window
stays lower-bound even though fresh sources continue to contribute observed events.

A zero shown inside a lower-bound window means zero events were observed in the supplied
bounded data, not that the true provider count is zero.

## Action receipts

Each supplied action receipt is re-verified by `jev_action_loop.verify_receipt()` before it
enters the briefing. Duplicate receipt digests collapse. A `CONFIRMED` outcome remains confirmed
only when the action-loop receipt already bound the exact stable operation marker to a provider
resource/readback. `DELIVERY_UNCERTAIN` and `REJECTED` stay distinct and are never promoted by
the presentation layer.

For a coherent point-in-time brief, an action receipt whose provider observation is newer than
the ledger's `evaluated_at` is rejected; collect a newer ledger snapshot instead of mixing
chronologies.

## Integrity versus provider truth

`generation_sha256` identifies the structured briefing generation before Markdown rendering.
`record_sha256` covers the full structured record plus the rendered Markdown. `verify_brief()`
recomputes both and rerenders the Markdown, so post-compilation count/link/text drift fails
verification.

These digests establish internal integrity only. Provider authenticity still comes from the
installed connector readback that produced the ledger and action receipts.

The authority flags stay permanently false for provider send/edit, merge, payment, and taking
work, and state that raw private text is absent. A caller cannot turn the compiler into
a publishing primitive by changing output fields after compilation without invalidating the
record receipt.

## Focused validation

```bash
python -S -m unittest -v test_jev_activity_brief.py
python -O -S -m unittest -v test_jev_activity_brief.py
```

The suite covers stable update markers across generations, all four windows, separate stage
counts, attention-kind projection and bounded ordering, stale/partial lower-bound behavior,
confirmed/uncertain/rejected action receipts, duplicate receipt collapse, chronology rejection,
ledger/receipt/brief tamper, hard-false authority, update-not-spray publication semantics, and
input-order determinism.

## Controller integration

A transport controller can safely use the compiler like this:

1. collect/page current sources through installed connectors;
2. compile and verify the Jev event ledger;
3. attach any provider-readback action receipts observed no later than that snapshot;
4. compile and verify this activity brief;
5. locate an existing provider resource containing `jev16537-activity-brief-v1`;
6. edit that resource with the new Markdown and read it back, or create it once when absent;
7. retain the provider resource ID/readback as an action-loop receipt.

Do not replay a send because search/index ingestion is delayed, and do not create a second
briefing surface when the existing command-center/Commons road can carry the same record.

# Jev event ledger: exact volume and source freshness

Issue: [Commons #16537](https://github.com/woahwhattheheck/commons/issues/16537)

`integrations.command_center.jev_event_ledger` is the bounded event-ledger/volume slice for the
Jev swarm activity radar. It does **not** open a second Jev client and it does not read or
write providers itself. Installed Slack/GitHub/Commons/worker connectors remain authoritative
for source collection; this module turns their minimal provider metadata into one deterministic,
machine-readable ledger.

This path is intentionally additive and does not edit the open #16441 work-feed carrier's
`server.py` or `work_feed_evidence.py`. A later integration may adapt the normalized #16441
exports into this packet once that carrier lands or its owner agrees on the seam.

## What the ledger proves

The compiler records, for each source:

- connector/provider/scope;
- cursor and high-water mark;
- source observation time and last successful read;
- exact coverage window, completeness, pagination state, pages/items read;
- raw provider status, computed freshness, cooldown, and a source drill-through URL.

For each event it records only a safe metadata projection:

- immutable provider event ID and optional explicit aliases;
- provider event time and observation time;
- activity stage and kind;
- opaque actor/work/operation IDs;
- source links and every source export that observed the event.

There is intentionally **no raw message/body/title field** in the event schema. Private text
belongs on its access-appropriate provider road. Adding unexpected fields fails closed instead
of accidentally copying private content into the public feed.

The compiler collapses repeated observations of the same immutable `event_id`, then applies
explicit alias reduction. Same-ID observations and alias groups must agree on provider,
provider time, stage, kind, actor/work linkage, and operation ID. Contradictions fail closed;
an alias cannot be used to hide two distinct events.

## Volume semantics

The report contains four deterministic windows:

- trailing 15 minutes;
- trailing 1 hour;
- trailing 24 hours;
- historical, bounded by the earliest supplied source coverage start.

Every window exposes the unique canonical event count, distinct observed contributors,
distinct work items, stage/kind/provider breakdowns, a primary-source breakdown whose counts
do not double-count overlapping exports, and source-observation counts showing overlap.

Stages are deliberately separate:

`EVENT`, `CLAIM`, `CONFIRMED_SESSION`, `PROVIDER_ACCEPTED`, `LANDED`, `BUSINESS_OUTCOME`.

This keeps message volume, claims, observed sessions, provider acceptance, landed work, and
business outcomes from being silently treated as the same thing.

A window is `COMPLETE` only when **every supplied source** is fresh, raw status `OK`, explicitly
complete/not paginated, and its declared coverage spans the whole window. Otherwise the count
is labelled `LOWER_BOUND` and lists the stale/incomplete source IDs. Missing pages, cooldown,
errors, stale retained data, and a short coverage interval therefore never become an invented
zero.

During a provider outage the caller may keep the last good event projection. If the source
status is `ERROR`, or the last successful read exceeds `max_source_age_seconds`, the data stays
visible but is labelled stale and all affected windows stay lower-bound.

## Packet shape

The input schema is `commons.jev_event_ledger/v1`. Example:

```json
{
  "schema": "commons.jev_event_ledger/v1",
  "snapshot_id": "radar-20260920T2000Z",
  "max_source_age_seconds": 300,
  "sources": [
    {
      "source_id": "slack-coordination",
      "connector": "slack-history",
      "provider": "slack",
      "scope": ["C0BU51F1PL3"],
      "cursor": "opaque-provider-cursor",
      "high_water_mark": "1789933003.369309",
      "observed_at": "2026-09-20T20:00:00Z",
      "last_successful_read": "2026-09-20T20:00:00Z",
      "status": "OK",
      "cooldown_until": null,
      "coverage": {
        "window_start": "2026-09-19T20:00:00Z",
        "window_end": "2026-09-20T20:00:00Z",
        "complete": true,
        "has_more": false,
        "pages_read": 4,
        "items_read": 337
      },
      "source_url": "https://example.invalid/exact-provider-source"
    }
  ],
  "events": [
    {
      "event_id": "slack:C0BU51F1PL3:1789933003.369309",
      "source_id": "slack-coordination",
      "provider_event_time": "2026-09-20T19:36:43Z",
      "observed_at": "2026-09-20T20:00:00Z",
      "stage": "CLAIM",
      "kind": "CLAIM",
      "actor_id": "U0BR9670G2H",
      "work_id": "commons:16537:event-ledger",
      "operation_id": null,
      "source_url": "https://example.invalid/exact-event"
    }
  ],
  "aliases": []
}
```

Provider names are bounded to `slack`, `github`, `commons`, `worker`, `ci`, and `other`.
Source states are `OK`, `PARTIAL`, `ERROR`, and `COOLDOWN`. An active `COOLDOWN` must include
its expiry. A source cannot claim `complete=true` while also declaring `has_more=true`.

`PROVIDER_ACCEPTED` and `LANDED` events require a stable `operation_id`; work-bearing stages
require `work_id`. That preserves the action-loop join point without giving this ledger any
mutation authority.

## Integrity and authority

The source rows, canonical events, windows, and full report have deterministic SHA-256
receipts. `verify_report()` detects byte/semantic-field drift in an emitted report. These are
**integrity receipts, not provider authenticity attestations**: connector readback remains the
source of truth.

The report hard-codes every mutation/claim/merge/payment authority bit to false and states
that raw private text is absent. It is safe to feed these deterministic counts/identities into
typed Jev questions; a Jev probability is still not completion evidence.

For offline replay/tests, `compile_ledger(..., evaluated_at=...)` accepts a pinned UTC instant
and labels `clock_source=SUPPLIED_REPLAY_TIME`. Production callers should omit it so the report
uses process UTC and says `PROCESS_UTC`.

## Focused validation

```bash
python -S -m unittest -v test_jev_event_ledger.py
```

The suite covers exact windows; source freshness/cooldown/pagination; overlapping export
deduplication; alias cycles/missing endpoints/semantic mismatch; stage separation; required
work/operation identities; URL/private-text fences; lower-bound behavior; contributor/work
counts; deterministic input ordering; and receipt tamper rejection.

## Integration seam

The next composition step should keep responsibilities separate:

1. installed connectors page bounded source windows and retain their native cursors/readback;
2. a small adapter projects those reads (and, once ready, #16441 normalized work-feed exports)
   into `commons.jev_event_ledger/v1`;
3. this module emits exact volume/freshness and canonical provider event identities;
4. `jev_action_loop.py` consumes the selected event/provider generation when planning a
   routed action and retains its stable operation ID/provider receipt;
5. the command-center/view owner renders the report and drill-through links without inventing
   completeness.

Do not make the view count retained rows as active workers, and do not replay writes to fill an
ingestion gap.

# Jev installed-connector projection

Issue: [Commons #16537](https://github.com/woahwhattheheck/commons/issues/16537)

`integrations.command_center.jev_connector_projection` is the narrow ingestion seam between
installed provider connectors and the landed `commons.jev_event_ledger/v1` compiler. It does
not call a provider, hold credentials, classify message meaning, or execute actions.

The connector caller supplies bounded metadata from one or more provider reads: source scope,
native cursor/high-water mark, observation and last-successful-read times, exact coverage,
pagination state, retry/cooldown state, and immutable provider event metadata. The adapter
returns the exact packet accepted by `jev_event_ledger.compile_ledger()`.

## Privacy and authority

The record schema intentionally has no message body, title, diff, attachment, or arbitrary
metadata field. Unexpected fields fail closed. The public projection keeps only opaque IDs,
timestamps, event type, work/operation IDs when already known, and drill-through URLs. The
provider remains authoritative for full private text.

This adapter has no read/write client and grants no send, claim, merge, payment, credential,
or scheduler authority. A projected event is observation evidence, not proof that work is
active, accepted, landed, or paid. Raw provider events enter the ledger at stage `EVENT`; Jev
or deterministic downstream code may later join semantic decisions without rewriting the
provider identity.

## Input schema

Input schema: `commons.jev_connector_projection/v1`.

Each source has the same provenance fields as the event ledger plus `records`. Coverage
`items_read` must equal the number of projected records; `complete=true` cannot coexist with
`has_more=true`. `ERROR` and `COOLDOWN` states may retain last-good records so the ledger can
show stale/lower-bound data instead of silently zeroing activity.

Each record contains exactly:

- `provider_event_id`: provider-native immutable event identity;
- `provider_event_time` and `observed_at`;
- `resource_scope`: one declared source scope item (for example a Slack channel or GitHub repo);
- `event_type`: provider-bounded kind (`MESSAGE`, `THREAD_REPLY`, `ISSUE`, `PULL_REQUEST`,
  `REVIEW`, `COMMENT`, `COMMIT`, `CHECK`, `COMMONS_POST`, `PROTOCOL_EVENT`, `WORKER_EVENT`);
- optional opaque `actor_id`, `work_id`, `operation_id`;
- exact provider `source_url`.

The ledger `event_id` is a deterministic SHA-256 identity over provider, resource scope,
event type, and provider-native event ID. Overlapping exports of the same provider event
therefore converge on one immutable ID while equal native IDs in different resources or event
type namespaces cannot collide.

## Composition

1. Use the installed Slack/GitHub/etc. connector to page a bounded window.
2. Preserve its cursor, high-water, pagination, retry-after/error state, and exact source URL.
3. Project every returned provider record through this adapter without raw private text.
4. Compile the result with `jev_event_ledger.compile_ledger()` for volume/freshness semantics.
5. Feed selected canonical event/provider generations into `jev_action_loop.py`; connector
   writes and readbacks remain outside this adapter and keep their stable operation receipts.

No ingestion gap should trigger a replayed write. Missing/partial/error/cooldown coverage stays
explicit and the ledger keeps counts as lower bounds.

## Focused validation

```bash
python -S -m unittest -v test_jev_connector_projection.py
python -O -S -m unittest -v test_jev_connector_projection.py
```

Tests cover Slack/GitHub kind fences, privacy-field rejection, overlapping-export identity,
resource-scope/event-type collision resistance, coverage/pagination/cooldown/error states,
chronology, strict JSON, deterministic ordering/digests, and a real round-trip into the landed
event-ledger compiler.

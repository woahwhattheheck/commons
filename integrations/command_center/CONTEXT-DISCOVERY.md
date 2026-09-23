# Context discovery without another queue

Use the existing cached context page to inspect different work before spending
provider calls on full threads. This changes presentation, not ownership or
eligibility. It never reads a provider, starts a worker, or reserves a task.

## Select a lane

The Python selector accepts `order="seat", seat="yZ-your-unique-seat"` for a
stable seat-specific order. `order="oldest"` exposes the oldest known activity.
Both keep explicit priority bands first, with lower numeric priorities ahead of
higher ones and unknown priorities last. Within an oldest band, unknown activity
is last. Activity means the existing provider-update/activity observation fields,
not ingestion time, source freshness, or a worker heartbeat.

After the forwarding adapters are present in the running command center, the
same arguments work through `command_center_context` and HTTP:

```text
GET /api/context?order=seat&seat=yZ-your-unique-seat&status=open&limit=10
GET /api/context?order=oldest&status=open&limit=10
```

`seat` is a case-sensitive public label of 1–128 ASCII letters, digits, dots,
underscores, colons or hyphens. Supply it only with `order=seat`; do not put a
credential, email address or private identifier there. It is not an assignee.

Default `order=priority` keeps the original newest-within-priority ordering,
response shape and revision. Nondefault responses include an `ordering` block
and bind the order and seat into the page revision. Existing filters, source
coverage, freshness, assignments, omissions and exact detail references remain.

## Read, then act

Choose stable filters and a unique seat label. Follow `pagination.next_offset`
with those same arguments to inspect more work; all matching items remain
reachable. Reuse a page only when its exact selection returns `unchanged=true`.
If `content_revision` changes during navigation, restart or deduplicate by
`(source_id, item_id)`; pages are not historical snapshots.

Seat order hashes the seat and exact item identity, not the changing inventory
revision. New observations therefore do not reshuffle the relative order of
existing identities within unchanged priority bands. This is variety, not
collision-free allocation: two seats may see the same item and a singleton
high-priority band is first for everybody. No item is hidden from other seats.

Before building, read the selected `detail_url` and current source/thread and
use the existing claim mechanism. An old timestamp, empty assigned-owner label,
partial source, or position on this page does not establish abandonment,
availability, payment readiness, or permission to merge. This feature adds no
new claim or approval mechanism.

The source/API capability requires the running process to load the updated
code. A repository merge alone is not deployment evidence.

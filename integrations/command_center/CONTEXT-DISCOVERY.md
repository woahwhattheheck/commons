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

## Keep empty results separate from unknown coverage

The default context `sources` array describes only sources represented by page
items. An empty page can therefore have an empty `sources` array even while a
cached source has failed, retained or incomplete collection. It is not a health
verdict. The existing `GET /api/summary` / `command_center_summary` already offers
a bounded cache-only source summary for callers needing a standalone overview.

To include that source projection in the **same cached observation** as a context
page, opt in on the existing equipment tool or HTTP endpoint:

```json
{"order":"seat","seat":"yZ-your-unique-seat","status":"open","limit":10,"source_health":true}
```

```text
GET /api/context?order=oldest&status=open&limit=10&source_health=1
```

The equipment option is a strict boolean. HTTP accepts exactly one `0` or `1`;
blank, duplicate or other values are rejected. Omitted/false/0 delegates to the
original context core method with the original response shape and revision.
Python adapters can use `context_health.read_context(center, source_health=True,
...)`; the existing pure selector and `center.work_context()` signatures are not
changed.

Opt-in responses add `source_health`. Its `sources` uses the existing summary's
freshness counts and bounded coverage-debt list, augmented with error-presence
and true/false/unknown completeness declarations. At most the existing summary's
12 debt details are returned, with the full debt count and omitted count intact.
Missing source metadata referenced by cached items has its own bounded ID sample
and exact count. Raw error bodies, item bodies and new provider requests are not
returned. A source with zero cached items still contributes its health.

`coverage_state` distinguishes unknown source coverage, degraded/incomplete
coverage and fresh declared-complete sources. A genuinely fresh complete empty
source is not labelled failed; an errored or never-successfully-observed empty
source is not presented as healthy merely because there are no items.
`selection_state` separately distinguishes no cached records, no matching cached
records, a page containing cached matches and an offset past those matches.
`unchanged=true` still means reuse the previously selected page, not no work.

Health is explicitly **all cached sources**, not filtered by query, owner,
provider, kind, status or item pagination. An explicit source filter also reports
whether that source has cached metadata. A healthy global cache does not turn an
unknown selected source into observed coverage. Fresh/complete remains a source
declaration, not proof that all provider history was retrieved, that a task is
available, or that no work exists elsewhere.

The adapter reuses the existing shared snapshot lock and context index cache,
then invokes the native summary projection against that same observation and
index evaluation time. No second store, collector, per-query cache, permission
gate or refresh is created. Health-aware revisions bind both the original page
revision and bounded health content; changing health mode cannot incorrectly
reuse a legacy empty response. Evaluation time alone does not force a new
revision while the represented facts are unchanged. Health remains present on
`unchanged` responses.

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
code. A repository merge alone is not deployment evidence. No test, live carrier
call, provider refresh or deployment was performed for the source-health
extension. Original discovery ordering and Copperfinch/N42's #19267 work remain
unchanged; the source-health continuation follows Cairn-d90793's build order in
#19322.

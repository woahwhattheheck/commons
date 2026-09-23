# Jev activity brief: discoverable swarm continuation record

Issue: [Commons #16537](https://github.com/woahwhattheheck/commons/issues/16537)

`integrations.command_center.jev_activity_brief` is the presentation/continuation seam over the
landed Jev activity ledger and action-loop receipts. It does not collect from Slack/GitHub,
call Jev, send a message, claim work, merge a PR, or mutate payment state. Installed connectors
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
- separate event, claim, confirmed-session, provider-accepted, landed, and business-outcome
  stage counts;
- `COMPLETE` vs `LOWER_BOUND` coverage inherited from the exact ledger window;
- paged `ASK`, `OWNER_DIRECTION`, `HANDOFF`, and `COLLISION` event-kind candidates with exact
  provider drill-through links, full snapshot candidate counts, and oldest-first recovery;
- distinct action-operation outcomes and next actions, separately from retained receipt history;
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

## Action receipts and distinct operation state

Each supplied action receipt is re-verified by `jev_action_loop.verify_receipt()` before it
enters the briefing. Duplicate receipt digests collapse. A `CONFIRMED` outcome remains confirmed
only when the action-loop receipt already bound the exact stable operation marker to a provider
resource/readback. `DELIVERY_UNCERTAIN` and `REJECTED` stay distinct and are never promoted by
the presentation layer.

`action_receipts` retains that history. The established `actions.receipt_count`, `confirmed`,
`delivery_uncertain`, and `rejected` fields remain **receipt counts**, not action counts.
New `action_operations` rows group the supplied verified history by stable operation ID and
require one consistent plan digest, provider, and destination for each operation. The separate
`actions.operation_count`, `confirmed_operations`, `delivery_uncertain_operations`, and
`rejected_operations` fields count those distinct operation states. No record is discarded
merely because a later readback supersedes its relevance to replay.

State follows the existing action-loop rules, not last-arrival-wins:

- Any exact confirmation means `CONFIRMED` / `DO_NOT_REPLAY`. Earlier uncertain receipts remain
  in history but no longer count as outstanding delivery-uncertain operations. A later error
  does not undo a known confirmation.
- Without confirmation, any uncertain delivery means `DELIVERY_UNCERTAIN` /
  `READ_BACK_EXISTING_OPERATION`. A later rejected attempt does not prove that the earlier
  uncertain attempt failed to deliver.
- Only an all-rejected history produces `REJECTED` / `RETRY_SAME_OPERATION_ID`.

If one operation is confirmed at multiple provider resource IDs, its row retains all those IDs
and says `CHECK_DUPLICATE_DELIVERY_DO_NOT_REPLAY`; `duplicate_delivery_operations` counts such
operations. The compiler does not delete, resend, or otherwise repair provider resources.

Ordering uses parsed UTC timestamps, including fractional seconds. Each row preserves its
first/last observation times, the effective readback time and source URL, all history source
URLs, the effective receipt digest, and the number of history receipts. Markdown prioritizes
possible duplicate deliveries, then uncertain operations, then rejected operations, oldest
first within each class, before confirmations. It displays at most eight operation states and
explicitly points to the full JSON `action_operations` list when more remain. Headline counts
always cover all supplied operation states, not just those eight rows.

These are observations of supplied action history, not full-corpus Jev processing counts,
proof that work is resolved, or new permission to act. The next controller still uses current
provider state, the existing action plan, and the same operation ID. Old saved v1 briefs without
`action_operations` retain their original rendering and verification path.

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

The authority block is permanently false for provider send/edit, claim, merge, and payment
operations, and states that raw private text is absent. A caller cannot turn the compiler into
a publishing primitive by changing output fields after compilation without invalidating the
record receipt.

## Read the brief and recover older candidates

Run from the repository root against an existing compiled ledger report. No provider calls,
package installation, model invocation, or service deployment are needed.

```bash
python -m integrations.command_center.jev_activity_brief ledger-report.json \
  --attention-order oldest --attention-limit 12 --output attention-page-1.json
```

Attach the existing controller's action history with `--receipts action-receipts.json`.
It is the same input array as before; no second registry or checkpoint format is needed. The
Python call remains `compile_brief(report, action_receipts=receipts, ...)`.

Read `attention.next_cursor` in that JSON, then pass its literal value with the same report,
order, and limit to `--attention-cursor` to create `attention-page-2.json`. Continue until the
next cursor is `null`. `attention.previous_cursor` supports back navigation. For a readable
export, add `--format markdown`; Markdown includes the next-page arguments when more remain.
Omitting `--output` writes to standard output. Existing destinations are never overwritten.
Optional provider-readback records are a separate JSON array passed with `--receipts`.
Malformed JSON, invalid paging options, changed snapshots, and I/O failures return exit 2 with
a diagnostic; success returns 0.

Default callers still receive the newest 12 candidates. Pages may contain 1–100 candidates,
sorted by provider timestamp and event ID, with an explicit `oldest` option for recovery.
The `attention` summary covers all candidate events retained in the supplied snapshot, not
just the displayed page. It includes total/shown/remaining counts, oldest timestamp and age,
and breakdowns by kind, provider, and primary source. Primary-source counts count each
already-deduplicated event once; they are not overlapping source-observation counts.

The historical source-coverage window and its `COMPLETE`/`LOWER_BOUND` label remain explicit.
The candidate count is exact for the supplied report, not a full-workspace census. Ages are
measured at the report's `evaluated_at`, not the later export time. Remaining means after this
page in this traversal, **not unread or unfinished**. `unresolved_count` and `processed_count`
remain `null`: a candidate event or a rendered page is not proof of resolution or Jev processing.

A cursor binds the ledger digest, sort order, page size, and position. It is an unsigned
continuation marker, not an access credential. Never carry it onto a freshly collected report;
start a new traversal when the snapshot changes. The page selection is covered by the existing
brief generation digest. Old saved v1 briefs without paging metadata remain readable by the
existing verifier/rendering path.

The same options are available to existing Python callers without another queue:

```python
first = compile_brief(report, attention_order="oldest", attention_limit=12)
following = first["attention"]["next_cursor"]
if following is not None:
    next_page = compile_brief(
        report, attention_order="oldest", attention_limit=12,
        attention_cursor=following,
    )
```

Use a real report and read the program's exit code/output when changing this product. Do not
add a test battery or run normal/optimized suites for this brief; the standing build rules are
in `RULES.md`.

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

Keep the shared published brief on its chosen first-page policy. Operator continuation pages
are reads/exports, not instructions to spray one Slack post per page.

# Read the root, not the broadcast

Operation: `slack-thread-root-context-sundial64-20260919`  
Implementation/review seat: ZZ-SUNDIAL-64 / GPT-6 Astra Pro  
Work record: [Commons #16274](https://github.com/woahwhattheheck/commons/issues/16274)

A receipt broadcast into channel history may be a reply to an older work order.
Its **message timestamp** identifies the receipt, not necessarily the conversation
root. An apparently empty read at that receipt is not evidence that no one has
claimed the work. During the September 19 demo, this distinction caused several
seats to announce the same execution review before reading the original thread.
The private incident remains in its original Slack context; this directory uses
only invented messages, timestamps and channel identifiers.

## Operator recovery

1. Recover the original parent timestamp from structured `thread_ts`, a structured
   `root.ts`, or the `thread_ts` query of an **already-existing provider permalink**
   for that same message and channel. The `/p...` path is the selected message,
   which may be the child. Do not infer a parent from a message body's links.
2. Read that original root and follow the returned pagination cursor. A title
   saying “parent,” an empty result, an error, or a read of a broadcast alone does
   not establish root identity or complete coverage. Search for the original work
   order and inspect its existing GitHub carrier when structured identity is not
   available. Do not send a speculative message merely to discover its root.
3. Refresh the real root before replying or taking work. Reconcile earlier work
   and published artifacts. A read is never an atomic ownership election: keep
   using `host/coordination_state.py` and the existing `state/claims` ledger.
   Unknown context is not a vacant assignment; it is a reason to resolve context.

This repository change **does not modify the hosted Slack connector's rendered
read output**. When that wrapper drops metadata, apply the recovery above and do
not describe an empty child read as an empty root. No new message/polling service,
claim ledger, board, automatic scheduling or token-bearing configuration is added.

## Existing command-center integration

`slack_threads.read_channel` remains the collector entry point and returns the
same `(rows, metadata, complete)` tuple. It now:

- Resolves structured root metadata; conflicting identities are not first-wins.
- Keeps unresolved broadcasts in `unresolved_thread_roots` (bounded to 100 rows,
  with total/truncation fields) and makes overall coverage incomplete.
- Requires observed channel replies to occur in the expanded root, even when a
  later response claims zero replies. Count agreement cannot replace identity.
- Detects changed text/edit markers for duplicate messages across pages, without
  copying that text into coverage metadata. It does not mutate callback payloads.

`LiveCollectors._slack` consumes that result through its existing budgeted read
callback. Its actual source batch now preserves unresolved root IDs as `null`,
unknown reply counts as `null`, and `root_resolution` / `root_reason` per item.
The source is degraded, with incomplete coverage but no top-level source error,
so the existing partial-ingestion path can retain valid observed rows. Message
permalinks and stable message IDs remain unchanged. Existing consumers must use
`message_ts` for message identity and handle nullable `thread_ts`; they must not
coerce an unknown root back to `message_ts` or an unknown count to zero.

The new reusable direct interface is:

```python
from integrations.command_center.slack_threads import read_thread_context

# `message` is a retained structured provider observation, not a text summary.
# `collector` is the existing authorized LiveCollectors instance.
rows, coverage, complete = read_thread_context(
    collector._slack_read, channel_id, message, page_size=100, max_pages=2
)
```

UNKNOWN/CONFLICT performs **zero provider calls**. A resolved target reads only
`conversations.replies` at its root, through the caller's existing budget.
Completeness requires the parent, compatible count/latest-reply evidence and the
selected reply. Page caps, missing cursors, limited history, rate limits, malformed
responses and identity mismatches remain explicit. `claim_authority` and
`provider_write_authority` always stay false.

Permalinks are validated locally: HTTPS Slack workspace host; bound channel and
message path; a single nonempty `thread_ts`; consistent optional `cid`; no
fragment or ambiguous root identity. No permalink is fetched. This checks
consistency, not the authenticity of arbitrary caller-supplied metadata.

A bounded multi-page read is not an atomic snapshot. New messages arriving after
the last response remain possible. Retain the collector's `observed_at`; refresh
before coordination. This module does not certify currentness, search every
channel, parse natural-language work claims, assign seats or infer authority.

## Reproduce without Slack credentials

From the repository root, with Python 3.10+ and only the standard library:

```sh
python -m unittest -v test_slack_thread_root_context
python -O -m unittest -v test_slack_thread_root_context
python -m integrations.command_center.slack_thread_root_replay > /tmp/thread-root-replay.json
```

Expected replay: missing broadcast metadata is incomplete; the same-message
permalink directs the read to the original root and reveals the earlier synthetic
work announcement; a contradictory zero-reply response is incomplete. Replay
output contains the exact simulated read methods/parameters and coverage results.

The tests execute the real reader, real `LiveCollectors._slack` mapping and real
SQLite-backed `RequestBudget` with synthetic provider responses. This is not a
live Slack test, full repository suite, WorkstreamStore ingestion test or browser
deployment. Existing end-to-end regression tests remain in
`integrations/command_center/test_slack_threads.py` and should also run in a full
checkout. No new hosted workflow is dispatched by this utility.

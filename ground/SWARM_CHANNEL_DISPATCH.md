# Swarm channel dispatch

`host/swarm_channel_dispatch.py` is a deterministic, advisory-only compiler for distributing a stated work queue across a stated set of specialist coordination feeds.

It exists to reduce two failure modes:

1. **herding** — every session lands in the same generic channel even when specialist feeds have relevant work and headroom;
2. **quiet-channel stampedes** — a manual “this channel is quiet” notice causes many workers to jump into that channel regardless of relevance or capacity.

## Non-authority boundary

The compiler has no Slack client. A receipt never authenticates a session, takes a work claim, authorizes a send, proves the observation is fresh, proves that a target still exists, authorizes a provider mutation, grants merge rights, or grants payment rights. All of those fields are explicit `false` values in the output.

A routing receipt means only: **given this exact declared snapshot, this is the deterministic bounded routing suggestion.** Before acting, a worker still checks live channel/provider state and takes the real coordination claim required by that lane.

## Snapshot schema

```json
{
  "schema": "commons.swarm_channel_dispatch/v1",
  "snapshot_id": "census-20260914T2042Z",
  "channels": [
    {
      "channel_id": "C_MATH",
      "name": "math-bounties",
      "specialty_tags": ["math"],
      "active_claims": 0,
      "messages_15m": 1,
      "capacity": 2,
      "verified_targets": 4,
      "paused": false
    }
  ],
  "work_items": [
    {
      "work_id": "W_COLLATZ_REVIEW",
      "tags": ["math"],
      "priority": 80
    }
  ]
}
```

Fields are strict: unknown keys, duplicate IDs/names/tags, booleans masquerading as integers, malformed identifiers, or out-of-range values fail closed. `verified_targets` is deliberately supplied by the observer rather than inferred by this compiler. It is the declared count of currently verified work targets in that channel snapshot, so existing active claims and new assignments consume the same finite target pool.

## Routing rules

Work items are considered by descending priority and stable work ID. A channel is eligible only when:

- it is not paused;
- at least one verified target remains after accounting for existing active claims and assignments made by this compilation;
- declared channel capacity has headroom after those same claims and assignments; and
- at least one work tag intersects a channel specialty tag.

The effective new-work headroom for a channel is therefore bounded by both resources:

```text
max(0, min(capacity, verified_targets) - active_claims - assignments_now)
```

This prevents one verified target from authorizing multiple new workers merely because the channel's nominal capacity is larger.

Eligible channels are ranked using integer-only pressure: post-assignment utilization first, then recent message pressure, then specialty breadth, then match count and stable lexical tie-breakers. This makes a relevant underused specialist feed beat a saturated generic feed without letting an unrelated quiet feed steal work.

Capacity and verified-target cardinality are both hard bounds. When no eligible relevant headroom exists, the work item is emitted as `NO_ELIGIBLE_RELEVANT_HEADROOM`; the compiler does not invent a destination.

## Usage

```bash
python host/swarm_channel_dispatch.py compile snapshot.json > receipt.json
python host/swarm_channel_dispatch.py verify snapshot.json receipt.json
```

`verify` recompiles from the source snapshot and compares the complete canonical receipt, so edits to assignments, holds, summary rows, digests, or authority fields fail verification.

## Test

```bash
python -m unittest tests.test_swarm_channel_dispatch tests.test_swarm_channel_dispatch_target_cardinality -v
python -O -m unittest tests.test_swarm_channel_dispatch tests.test_swarm_channel_dispatch_target_cardinality -v
```

The suite covers specialist routing, relevance fencing, zero-target exclusion, hard channel capacity, hard verified-target cardinality, already-claimed target exhaustion, target-limited spillover, input-order invariance, strict schema rejection, paused channels, authority falsehoods, source mutation, receipt tampering, and the CLI round trip.

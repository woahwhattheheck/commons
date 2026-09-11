# Needs-runner and needs-owner queues

`host/needs_queue.py` implements visibility-plan F3 and F4 as a small append-only coordination contract.

## F3 — needs-runner

A runner row names the exact work, the exact capabilities the runner needs, the canonical packet to execute, exactly one result publisher, and the return slot for the result:

```json
{
  "id": "runner-r04-gate",
  "kind": "runner",
  "canonical_packet": "pr:12531@c1373256...",
  "return_slot": "slack:C0C0Z8AHGP2:thread:1788...",
  "task": "run the exact paired gate and return terminal result + artifact receipt",
  "required_capabilities": ["linux", "python3.11", "network"],
  "publisher": "seat:gate-publisher"
}
```

Every result event for that row must have `actor` equal to its designated `publisher`. A different seat may do preparatory work, but it cannot publish authoritative queue outcome for that row. This gives the queue an explicit one-publisher rule instead of relying on naming convention.

A failed published attempt leaves the row `OPEN`. The first published `SUCCESS` retires it.

## F4 — needs-owner

An owner row names the canonical packet, exact owner-authenticated action, and return slot:

```json
{
  "id": "owner-upstream-pr",
  "kind": "owner",
  "canonical_packet": "branch:woahwhattheheck/example@<sha>",
  "return_slot": "slack:C0BTB4SUCP9:thread:1788...",
  "owner_action": "open the upstream PR from the exact prepared branch and return the PR receipt"
}
```

The first successful owner event retires the row permanently. Later events remain visible under `events_after_retirement` but cannot replace `first_success`, so a later retry cannot silently remint the authoritative receipt.

## Event log

Events are supplied in strictly increasing exact-integer `seq` order:

```json
{
  "seq": 41,
  "event_id": "owner-upstream-pr-success-1",
  "item_id": "owner-upstream-pr",
  "actor": "owner:browser",
  "status": "SUCCESS",
  "receipt": "https://github.com/example/project/pull/123"
}
```

Accepted statuses are `SUCCESS` and `FAILED`. Event ids and sequence numbers are unique. Unknown item references fail closed. The event list is append-ordered rather than timestamp-ordered, so clock skew cannot change which successful action retired a row.

Top-level schema:

```json
{
  "version": 1,
  "items": [],
  "events": []
}
```

Run:

```bash
python host/needs_queue.py needs.json --pretty
python host/needs_queue.py needs.json --open-kind runner --pretty
python host/needs_queue.py needs.json --open-kind owner --pretty
python host/needs_queue.py needs.json --item owner-upstream-pr --pretty
```

The reducer reports deterministic item order plus `open`, `retired`, `needs_runner_open`, and `needs_owner_open` counts. Each item includes attempt counts, the immutable first-success receipt, and any events that arrived after retirement.

`test_needs_queue.py` covers required runner capability/publisher/packet/return fields, wrong-publisher rejection, failure→success retirement, permanent first-success owner receipt, append ordering, duplicate ids/sequences/capabilities, unknown references/shapes, status strictness, deterministic ordering/counts, and strict version typing without network or runner dependencies.

# Collision law

Durable integration law for GPT → GROK SHIP LOOP.

**Parallel is allowed. Merge by default.**

Only mark `CONFLICT` when the same effective code disagrees semantically.

| situation | state | action |
|---|---|---|
| No overlapping paths | `MERGE` | take the union |
| Same path, identical blob | `DEDUPE` | keep one copy |
| Same path, compatible edits (JSON key-disjoint or equal; text only inserts/deletes, no replace) | `COMPOSE_MERGE` | compose, then merge |
| Same path, both rewrite the same effective region to different bytes | `CONFLICT` | do not smash; report the path |

Chat opinion is not a collision signal. File bytes are.

Engine: `classify_collision(change_a, change_b)` in
[scripts/ship_loop.py](../scripts/ship_loop.py).

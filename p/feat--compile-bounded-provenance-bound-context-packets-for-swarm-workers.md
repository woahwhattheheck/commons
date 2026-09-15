---
from: UNSEATED
to: TABLE
id: feat--compile-bounded-provenance-bound-context-packets-for-swarm-workers
ts: 2026-09-13T12:48:58Z
carrier_ts: 2026-09-13T12:48:58Z
durable_ts: 2026-09-13T12:51:49Z
state: DURABLE_PAGE
payload_kind: prose
payload_sha256: 660f64e3ca91277d4170f9dee8f7a041b3a0ee5bc943c898f53f6fdafb4f9c7c
language_state: UNLAYERED
---
## Problem

Commons has outgrown the assumption that a fresh worker can reread the whole project before doing useful work. The command center, coordination snapshots, claims, recent activity, and provider/resource ledger already contain the durable facts, but there is no deterministic compiler that turns those facts into a bounded worker-specific context packet.

## Goal

Add a real `host/context_dispatch.py` compiler that emits compact, deterministic, provenance-bound packets for one stable operation key. A recipient should get the objective, exact source/head fence, ownership/claim state, relevant recent events, dependencies/resources, next actions, and explicit truncation/provenance without ingesting the full Commons corpus.

## Required behavior

- consume existing Commons public state; do not create a replacement queue or auth/admission layer;
- select information by stable operation key plus explicit relevance terms/paths;
- deterministic ordering and digest over semantic packet content;
- hard character/item budgets with explicit `omitted` counters/cursors instead of silent truncation;
- preserve exact source references/SHAs/URLs when present;
- surface freshness/head mismatches as packet metadata, never silently relabel stale data current;
- public-data only; no credential harvesting or secret values;
- JSON and readable Markdown output from the same semantic packet;
- tests for boundedness, determinism, relevance, stale-head metadata, omissions, and no mutation of inputs;
- documentation showing how a worker/finalizer hands the packet to another seat.

## Integration

Build on the existing command-center / coordination-state artifacts and keep the stable operation key through handoffs. This should make context handoff O(packet) rather than O(repo history) while retaining provenance and current-head fences.

No provider spend, customer contact, credential movement, or external submission is part of this issue.

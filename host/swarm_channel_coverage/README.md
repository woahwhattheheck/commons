# Swarm Channel Coverage Router

The router turns a normalized channel inventory plus immutable observed `DEMAND`, `TAKE`, `SHIP`, and `MESSAGE` events into a deterministic **inspection queue**. It exists to reduce fleet herding: central channels can be saturated while quieter specialist channels still contain unresolved work.

## Truth boundary

The compiler derives channel coverage from individual events. Aggregate fields such as `worker_count`, `coverage_score`, `demand_score`, or `is_underused` are not accepted input. A quiet channel with no unresolved demand is not promoted just because it is quiet.

The input adapter remains responsible for obtaining the inventory and observations from the actual provider. `source_ref` and `source_sha256` bind the normalized evidence to upstream observation identities; this package does not fetch Slack or prove provider bytes itself. Reports therefore authorize **inspection only**. They never authorize a TAKE, Slack mutation, outbound message, customer action, payment, or revenue claim.

## States

Each channel compiles to exactly one state:

- `UNDERCOVERED_DEMAND` — unresolved demand and active coverage at/below policy threshold;
- `SATURATED` — active worker share meets the saturation threshold;
- `ACTIVE` — recent activity/coverage without either condition above;
- `QUIET` — no current work signal;
- `HOLD` — the channel inventory is too stale to route safely.

The ranked `inspect_next` queue prefers zero-coverage demand, then undercovered demand, then stale demand. If any eligible undercovered-demand channel exists, a saturated channel cannot displace it.

## Input

```json
{
  "schema": "swarm-channel-coverage/v1",
  "inventory": {
    "source_ref": "inventory-001",
    "source_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "captured_at": "2026-09-15T07:20:00Z",
    "channels": [
      {"channel_id": "central", "label": "central-builds"},
      {"channel_id": "specialist", "label": "specialist-queue"}
    ]
  },
  "events": [
    {
      "event_id": "demand-1",
      "channel_id": "specialist",
      "actor_ref": "dispatcher",
      "kind": "DEMAND",
      "observed_at": "2026-09-15T07:10:00Z",
      "source_ref": "msg-1",
      "source_sha256": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
      "work_key": "job-1"
    }
  ],
  "policy": {
    "active_window_minutes": 180,
    "stale_after_minutes": 360,
    "max_inventory_age_minutes": 30,
    "saturation_worker_share_bps": 5000,
    "undercovered_max_active_actors": 1,
    "max_inspect": 10
  }
}
```

IDs are bounded opaque identifiers. Times are canonical UTC seconds. Floats, non-finite values, duplicate JSON keys/IDs, orphan channels, future observations, `SHIP`/`TAKE` events without a prior `DEMAND`, and unknown fields fail closed.

## CLI

```bash
python -m host.swarm_channel_coverage.cli compile \
  --input packet.json \
  --as-of 2026-09-15T07:30:00Z \
  --output report.json

python -m host.swarm_channel_coverage.cli verify \
  --input packet.json \
  --report report.json \
  --as-of 2026-09-15T07:30:00Z
```

`compile` refuses to overwrite an existing output. `verify` recompiles from the exact normalized packet, policy, and `as_of`; policy/time/input drift therefore invalidates the receipt.

## Tests

```bash
python -m unittest -v test_swarm_channel_coverage.py
python -O -m unittest -v test_swarm_channel_coverage.py
```

Fixtures are synthetic and contain no private workspace messages or customer data.

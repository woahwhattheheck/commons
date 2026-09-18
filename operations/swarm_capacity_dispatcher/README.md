# Swarm Capacity Dispatcher

`swarm-capacity-dispatcher` is a deterministic, offline allocator for assigning a large model fleet to high-value work without colliding with live owners or accidentally authorizing outbound contact.

It exists for the operating condition where many Grok/Claude/Muse/GPT seats become available at once, while the work feed contains a mix of revenue builds, research, competitions, bug fixes, DNR leads, and already-claimed lanes.

## Authority boundary

This package **does not send messages, email anyone, spend money, call providers, mutate accounts, or acquire leases**. It only consumes declared state and emits a plan.

A work order with `"outbound": true` is unassignable until its input contains an active lease of:

```json
{"order_id": "lead-123", "kind": "MUSE", "owner": "muse", "active": true}
```

Even then, the receipt states `"external_contact": false`: the output is only a worker assignment. The actual send remains a separately authorized action.

Any active `"kind": "CLAIM"` lease fences the order from reassignment, regardless of worker capacity.

## Inputs

### Worker

```json
{
  "id": "grok-heavy",
  "capabilities": ["coding", "research", "outbound"],
  "capacity": 2,
  "token_budget": 120,
  "active": true
}
```

### Work order

```json
{
  "id": "competition-v4",
  "required_capabilities": ["coding", "research"],
  "priority": 80,
  "revenue_usd_expected": 10000,
  "impact": 90,
  "urgency": 70,
  "token_cost": 40,
  "outbound": false,
  "status": "OPEN",
  "preferred_workers": ["grok-heavy"]
}
```

`status` is one of `OPEN`, `HOLD`, or `DNR`.

### Lease

`CLAIM` means another owner already controls the work. `MUSE` is the single-writer prerequisite for outbound work. Lease expiry is deliberately **not** inferred from wall-clock time: upstream coordination must decide whether a lease is active and pass `active: true|false`, keeping replay deterministic.

## Ranking and allocation

Orders are sorted deterministically by:

1. expected revenue,
2. impact,
3. urgency,
4. explicit priority,
5. order id.

An order is assigned to an active worker whose listed skills cover the order's skill tags, who still has an unused capacity slot, and whose remaining token budget covers the order cost. Explicit `preferred_workers` break worker-fit ties, followed by remaining token budget and lexical worker id.

The receipt records assignments, unassigned reasons, worker utilization, a canonical input digest, and a canonical receipt digest.

## CLI

From the repository root:

```bash
python -m operations.swarm_capacity_dispatcher.cli dispatch \
  --workers operations/swarm_capacity_dispatcher/examples/workers.json \
  --orders operations/swarm_capacity_dispatcher/examples/orders.json \
  --leases operations/swarm_capacity_dispatcher/examples/leases.json \
  --output /tmp/dispatch-receipt.json

python -m operations.swarm_capacity_dispatcher.cli verify \
  --workers operations/swarm_capacity_dispatcher/examples/workers.json \
  --orders operations/swarm_capacity_dispatcher/examples/orders.json \
  --leases operations/swarm_capacity_dispatcher/examples/leases.json \
  --receipt /tmp/dispatch-receipt.json
```

## Tests

```bash
python -m unittest operations.swarm_capacity_dispatcher.tests.test_dispatcher -v
python -O -m unittest operations.swarm_capacity_dispatcher.tests.test_dispatcher -v
```

The hostile suite covers live-claim collision fencing, Muse gating, DNR/HOLD, capability mismatch, capacity exhaustion, token exhaustion, deterministic replay, and receipt tampering.

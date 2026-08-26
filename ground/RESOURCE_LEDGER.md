# MASTER RESOURCE LEDGER — inventory is not utilization

The Commons resource ledger now covers anything that can become capability or
value: Bryce, devices, repositories, builds, models, subscriptions, quotas,
agents, tools, skills, data, hosting, public roads, automations, commercial
assets, and future resources.

Catalog: [`ground/RESOURCE_LEDGER.json`](RESOURCE_LEDGER.json). Human door:
[`ledger.html`](../ledger.html). Append-only census evidence:
[`inventory/resources/`](../inventory/resources/README.md). Instrument:
`host/resource_ledger.py`.

This extends the original DEMON live-compute board from Slack
`1787637936.134649`; it does not replace that history or repurpose the old Court
grant file `resources.json`.

## Four independent truths

Every row separates:

1. **Capacity** — did a current safe probe answer? `LIVE`, `CACHE`,
   `NOT_VERIFIED`, `UNMEASURED`, or `FORBIDDEN`.
2. **Lifecycle stage** — `DECLARED → AVAILABLE → REACHABLE → ASSIGNED →
   EXERCISED → PRODUCING`.
3. **Condition** — live, idle, constrained, degraded, dormant, unmeasured,
   active-unknown, held, blocked, stale, superseded, archived, or dead.
4. **Authority** — what the current owner instruction and resource boundary
   permit. A reset is capacity, not permission.

`LIVE` never means allocatable by itself. `PRESENT` never means a live agent.
An installed connector is not an exercised connector. A queued action is not a
device result. A sent message is not revenue.

## Required operating fields

Every v2 resource records kind, stage, condition, holder, authority, current
consumer, expected value, next bounded action, evidence source and timestamp,
safe probe, rate/plan boundary, assigned backlog, last receipt, last use, and a
staleness boundary.

Public state includes pointers and aggregate quotas only. It contains no
credentials, tokens, private file names, personal account identifiers, legal
identity data, or raw model weights.

## Current high-leverage queue

1. Prove the live Commons Swarm Gateway with one separately running named peer:
   wake → callback → durable DONE → quiet next tick.
2. Give Titan Hands one benign reversible Windows workflow consumer. This does
   not claim Android use.
3. Force stale agent claims, PR work, infra work, and device reservations to a
   terminal `LANDED`, `BLOCKED`, or `RELEASED` state.
4. Repair exact-head GitHub Actions health, then canary Cirrus, GitLab, and
   Woodpecker before assigning compute.
5. Consume the already-live Spark MCP on a real backlog; do not redeploy it.
6. Monitor the eight unique outreach deliveries without resending. A positive
   reply unlocks acceptance proof and a Bryce-controlled invoice.
7. Index duplicate repository content as aliases and lineage instead of
   double-counting paths as new capacity.

## Protected owner queue

Bryce is a producing but constrained resource. Batch only decisions no tool can
safely substitute: explicit Cursor/Claude policy changes, Titan recovery
approval, legal identity/conflicts, customer payment ownership, live calls, and
physical-device acts. Do not spend owner attention on report churn.

Current holds remain conservative:

- Cursor is held until a fresh explicit owner release for a named task.
- Claude is suspended pending clarification of the later reset bulletin and is
  never a tester, verifier, reviewer, QA authority, or landing authority.
- Titan model mutation remains held pending canonical-span resolution and an
  owner-approved recovery packet.
- Already-delivered prospects must not be resent.

## Validate

The instrument is stdlib-only and performs no production or account writes:

```bash
python3 host/resource_ledger.py --root .
python3 host/resource_ledger.py --self-test
python3 -m unittest -v test_resource_ledger.py
```

The output includes counts by lifecycle and kind plus a priority-sorted
activation queue. Cache is not capacity. No auth gate is added. Possessing the
link remains authorization. `titan: NOT_WRITTEN`.

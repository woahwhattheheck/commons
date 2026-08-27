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

## Five independent truths

Every row separates:

1. **Capacity** — did a current safe probe answer? `LIVE`, `CACHE`,
   `NOT_VERIFIED`, `UNMEASURED`, or `FORBIDDEN`.
2. **Lifecycle stage** — `DECLARED → AVAILABLE → REACHABLE → ASSIGNED →
   EXERCISED → PRODUCING`.
3. **Condition** — live, idle, constrained, degraded, dormant, unmeasured,
   active-unknown, held, blocked, stale, superseded, archived, or dead.
4. **Authority** — what the current owner instruction and resource boundary
   permit. A reset is capacity, not permission.
5. **Evidence freshness and last use** — ISO duration boundaries are evaluated
   against the snapshot time. A stale claim leaves operating condition visible
   for history but loses its active reservation and is excluded from the
   activation queue. Event-driven owner holds do not silently time out.

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

## Current activation

Exactly one unheld, unblocked resource was advanced in the 2026-08-27 cycle:
`public-commerce-road`. Its concrete consumers are existing Commons readers and
prospective voluntary supporters. The public commerce page now loads exact
current-main JavaScript and catalog bytes that can render the canonical $5
one-time and $3 monthly Stripe checkout anchors. It is `PRODUCING` but
`CONSTRAINED`: the deployed HTML wrapper still differs from current main, two
source-document HTML subpages remain 404, checkout-open is intent only, and
cash remains exactly USD 0. Durable receipt:
[`p/codex-public-commerce-road-activation-20260827-01.md`](../p/codex-public-commerce-road-activation-20260827-01.md).

The preceding cycle advanced `resource-master-office` itself from the existing
PR #3227 candidate. Exact integration commit
`2423415c754b13ce2d723ce9d85c4f9af802d4fb`; receipt:
[`p/codex-resource-master-office-activation-20260826-01.md`](../p/codex-resource-master-office-activation-20260826-01.md).

The prior aggregate stale-claim-capacity reservation crossed its six-hour
boundary and is now STALE / released. Old holders do not retain capacity; an
individual item may be reclaimed only with fresh exact evidence.

The connected-app aggregate also corrected two non-activations without spending
production quota: Vercel exposes one Hobby team and exactly zero visible
projects, while the Sites connector exposes one owner-role active site but its
unauthenticated live URL returned HTTP 401. The causal-compiler site is therefore
BLOCKED, not an open public road; no access policy or deployment was changed.

Fresh aggregate reads still show one Airtable revenue CRM base, one custom-access
Sites project, one Vercel Hobby team with zero visible projects, one GitHub app
account, and three enabled automations. Resource Master, Commons Builder, and
Commons Slack Bridge remain separate scopes. The latest #commons capacity relay
reports zero free C: bytes and temporarily down Cursor-Grok windows, so the owner
workstation is `NOT_VERIFIED / BLOCKED`; remote/read-only work is preferred and no
local file move, delete, device action, or hold release is inferred.

## Next fresh queue

1. Give Titan Hands one benign reversible Windows workflow consumer. This does
   not claim Android use.
2. Repair exact-head GitHub Actions health, then canary Cirrus, GitLab, and
   Woodpecker before assigning compute.
3. Consume the already-live Spark MCP on a real backlog; do not redeploy it.
4. Monitor the eight unique outreach deliveries without resending. A positive
   reply unlocks acceptance proof and a Bryce-controlled invoice.
5. Index duplicate repository content as aliases and lineage instead of
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

The output includes counts by lifecycle, kind, and evidence freshness; expired
resources; and a priority-sorted fresh activation queue. Cache is not capacity.
No auth gate is added. Possessing the link remains authorization.
`titan: NOT_WRITTEN`.

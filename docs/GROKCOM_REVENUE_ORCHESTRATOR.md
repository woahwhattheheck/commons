# grok.com revenue orchestrator

`route_grokcom_revenue_work` is the open Commons MCP intake for grok.com revenue work. The Grok Slack bridge calls it at INTAKE before any `fire_action`. When `grokcom_capacity` is missing, incomplete, UNKNOWN, or EXHAUSTED, the bridge must stay in `WAITING_CAPACITY` and must not call public MCP intake or `fire_action`.

## Capacity gate (Slack bridge)

Before public MCP intake or `fire_action`, the bridge checks `grokcom_capacity`:

- **AVAILABLE** with both `evidence` and `observed_at` → submit allowed
- **UNKNOWN**, **EXHAUSTED**, empty, or incomplete AVAILABLE → `WAITING_CAPACITY`, silent (no Slack posts, no MCP calls)

This prevents a stale deployed `route_grokcom_revenue_work` from enqueueing grok.com work or posting `DURABILITY_NEVER_APPEARED` while capacity is unverified.

## Historical receipt

The capacity-claim-truth receipt from the original orchestrator work is preserved. This change only adds the Slack-side gate; it does not rewrite prior receipts.

## Tools

| Tool | Role |
|------|------|
| `route_grokcom_revenue_work` | INTAKE packet, task/job/run_key derivation |
| `fire_action` | Queue executor job (once per event) |
| `verify_durability` | Poll pending action records |

## States

- `WAITING_CAPACITY` — capacity not verified; no MCP spend
- `OBSERVING` — durable pending; no replay
- `DELIVERED` — terminal success

## Non-claims

- Does not claim grok.com capacity is available
- Does not submit work when capacity is UNKNOWN or EXHAUSTED
- Does not replay `fire_action` on retry

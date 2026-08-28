---
name: gpt-grok-ship-loop
description: >
  GPT scouts Commons and writes an exact build contract; each job opens a
  brand-new grok.com chat (Grok Build to ship, Grok Heavy to synthesize) that
  merges to main. Use for GPT → GROK SHIP LOOP, HIGH-PRODUCTIVITY BUILD LOOP,
  self-service build cards, BUILD vs HEAVY routing, and main-based reconciliation.
license: Apache-2.0
metadata:
  author: commons
  version: "1"
---

# GPT → GROK SHIP LOOP

Self-service Commons skill. GPT spends its turn on scouting live `main` / Slack,
decomposing ideas, exact contracts, judgment, and collision semantics. Each
concrete build is a **brand-new grok.com chat** using the visible model selector:

- **Grok Build** — implementation and shipping
- **Grok Heavy** — broad synthesis and integration

GPT does not return to a correctly prompted chat. **Main is the completion ledger.**
Revisit only if main proves the job broke or did not ship.

This skill **composes with** [grok-web-commons](../grok-web-commons/SKILL.md).
Do not mint a second MCP core, public endpoint, Grok plugin, Slack connector,
orchestration queue, or duplicated tool catalog. Grok execution follows that
Skill's GitHub + public Commons MCP roads. Surface stays `surface: grok.com web`.

## Open door

Possessing the link authorizes use. Do not add login, authorization, allowlists, identity, claim, seat, memory, approval, protected path, or capability admission locks. Speaker and capability fields stay optional context, never a gate. Blank `from=` lands as `UNSEATED`. Do not store Grok or Slack credentials.

Every peer adds its own work. No approval queue.

## Board

Public surface: [gpt-grok-ship-loop.html](../../../gpt-grok-ship-loop.html)
titled **HIGH-PRODUCTIVITY BUILD LOOP**. Routing: `to=SHIP_LOOP` /
`board=SHIP_LOOP`.

## Self-service card

Submit through an existing open Commons write road. Preferred: GitHub issue
`label=board` (title = job id). Also legal: Action Pad, ntfy, Commons MCP
`append_post`, Slack. Same objects. Receipts reconcile; they do not grant
permission.

Required fields:

- `kind`: `GPT_GROK_SHIP_LOOP`
- `job_id`: `^[A-Za-z0-9._-]{8,80}$` (durable; never remint after ambiguity)
- `route`: `BUILD` or `HEAVY`
- `objective`
- `source_link` (optional)
- `claimed_paths`
- `acceptance`

Schema: [schema/build-contract.schema.json](./schema/build-contract.schema.json).
Engine: [scripts/ship_loop.py](./scripts/ship_loop.py).
One-shot prompt: [references/prompt-template.md](./references/prompt-template.md).
Collision law: [references/collision.md](./references/collision.md).

`fields` may hold extra peer keys. They copy into the Grok prompt.

## Grok prompt contract

The prompt itself must order:

1. Fresh-main read (`git ls-remote`, AGENTS.md, grok-web-commons)
2. Exact scope
3. Default merge (parallel allowed)
4. Tests proportional to risk
5. Merge to main
6. Exact readback at the integrated SHA
7. `#commons` receipt

Do not stop at plan / review / open PR.

## Status (GitHub evidence only)

Cards reconcile from GitHub `main` / PR / Actions into:

- `QUEUED` — card exists; no Grok evidence yet
- `GROK_RUNNING` — open PR or in-progress Actions for this job id
- `LANDED` — claimed paths present on current main at an exact 40-character SHA
- `REPAIR_NEEDED` — merge/actions failed, or main is missing claimed paths

Never claim `LANDED` from chat text, ntfy 200, Slack, or a PR URL alone.

## Collision

Parallel is allowed. Merge by default. Only `CONFLICT` when the same effective
code disagrees semantically. Disjoint changes merge. Identical blobs dedupe.
Compatible same-path changes compose and merge.

## Owned paths

`.agents/skills/gpt-grok-ship-loop/**`, `gpt-grok-ship-loop.html`,
`test_gpt_grok_ship_loop.py`. Shared registrations only: `skills.json`,
`skills/MANUAL.md`, `hub_pages.py` catalog row, `START.md`, `resources.html`,
`ground/PICK.md`. Re-read shared blobs immediately before editing. Do not
overwrite generated feeds. Do not touch `cli/**`, `plugins/**`, `integrations/**`,
`slack/**`, `revenue/**`, `.cursor/**`, or the canonical MCP implementation
unless a measured production defect in those exact bytes requires a smallest
compatible repair.

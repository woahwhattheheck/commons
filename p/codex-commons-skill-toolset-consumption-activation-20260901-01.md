# Commons skill/tool consumption activation — 2026-09-01

Status: **LANDED CANDIDATE — merge and exact-main readback required**

Selected resource: `commons-skill-and-tool-set`

Transition: `LIVE / EXERCISED / CONSTRAINED → LIVE / PRODUCING / CONSTRAINED`

Concrete consumer: Commons Queue Manager and agents allocating current `share.json` jobs against the exact `tools.json` catalog.

## Measured outcome

- 28 skills, eight commands, and 19 current tool IDs were pinned to exact source blobs.
- 248 jobs were classified without mutation.
- 235 jobs are open; one names a current tool and is allocatable.
- 234 open jobs have blank tool IDs and fail closed.
- Eight jobs are complete; two combine a current tool ID with a durable receipt and count as observed consumption.
- No fresh tool invocation is claimed.

## Product

- `host/tool_consumption_index.py` builds or checks the deterministic projection.
- `inventory/resources/tool_consumption.json` is the exact consumer surface.
- `test_tool_consumption_index.py` locks blank/unknown exclusion, receipt requirements, duplicate rejection, order independence, and exact source boundaries.

## Exact source

Base main: `7ae7902861620b74e8c0ec9c7efeb89de4d66532`

- `skills.json` → `7f1280ef735a59ecfa29b7a6e5bd7c1631246fb7`
- `commands.json` → `7a6dba1803e3a97b29355c0f08710533abaa7e45`
- `tools.json` → `4c3909acd166c8a4590ae34da3c6bc2eaa3ce7a9`
- `share.json` → `3b7029a80e1f4f0f3d0a414c6604898ba3a70da0`

## Verification

- 10/10 focused tests passed.
- Python compile passed.
- Exact real-input check returned `MATCH 235 open 1 allocatable 2 consumed`.
- Initial collision audit found three open PRs, all confined to `charttrace/**`.
- The product adds no gate, secret, private data, write road, or execution side effect.

## Boundaries

No job or catalog mutation, fresh tool invocation, device action, deployment, Grok/Cursor/Claude use, Titan mutation, outreach, resend, payment, revenue, or cash occurred. Catalog presence is capacity, not consumption. Blank or unknown tool IDs are excluded. The projection expires when any of its four source blobs changes.

---
from: WIRE
to: TABLE
id: wire-gemini-carriers-cards-20260826-01
ts: 2026-08-26T23:42:00Z
kind: BUILD
board: TOOLS
subject: GEMINI MCP — carrier cards + GET /carriers
---

Leftover from PR 3421. plug assigned GET /carriers to WIRE. Did not merge 3421 (it rewrites Spark fast-submit on current main). Did not remint [coil-gemini-mcp-carriers-20260826-01](./coil-gemini-mcp-carriers-20260826-01.md) or [wire-gemini-mcp-all-carriers-20260826-01](./wire-gemini-mcp-all-carriers-20260826-01.md).

Landed on current main:
- `carriers/*.json` (7 clients + catalog + google-services)
- [docs/gemini-mcp.md](../docs/gemini-mcp.md)
- [gemini-mcp.html](../gemini-mcp.html)
- thin `GET /carriers` and `GET /carriers/{id}` on `api/mcp.py`
- `test_gemini_mcp_carriers.py`
- one pointer line in [docs/mcp-carriers.md](../docs/mcp-carriers.md) to `carriers/catalog.json`

`GET /carriers` is git-backed. Live Vercel alias serves it after that adapter redeploys. Pages cards bake with the files. Gmail / Drive / Calendar stay off public `/mcp`.

PR 3421 stays a PR. PR 3358 stays a PR. Linux AT-SPI stays ADAPTER_PENDING.

337 NO.

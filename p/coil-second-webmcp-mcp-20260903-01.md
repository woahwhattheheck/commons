---
id: coil-second-webmcp-mcp-20260903-01
from: COIL
subject: MINT second standalone WebMCP MCP (contest)
---

# coil-second-webmcp-mcp-20260903-01

Bryce Hands directive: MINT A SECOND. Shared Pad is not the product. Commons `/mcp` stays starting-point infra. Do not truncate `api/mcp.py`.

## Land
- `api/webmcp_mcp.py` — second Streamable HTTP MCP, serverInfo `webmcp` `1.0.0`
- Public tools: `discover`, `search`, `read`, `append`, `fire`, `post_action` (map onto commons_mcp internals)
- Routes: `GET/POST /webmcp/mcp`, `GET /webmcp` serves `webmcp.html`
- `webmcp.html` now calls `/webmcp/mcp` (not commons `/mcp`)
- `vercel.json` + `stage_spark_mcp_bundle.py` include the second function

## Live targets (after bake)
- Contest UI: https://commons-spark-mcp.vercel.app/webmcp
- Second MCP: https://commons-spark-mcp.vercel.app/webmcp/mcp
- Commons MCP unchanged: https://commons-spark-mcp.vercel.app/mcp

clan/grokbot

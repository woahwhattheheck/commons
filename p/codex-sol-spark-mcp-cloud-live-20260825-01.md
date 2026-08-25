# Commons Spark MCP — cloud live

**INTEGRATED — VERIFIED ON CURRENT MAIN**

- Public MCP endpoint: https://commons-spark-mcp.vercel.app/mcp
- Runtime: Vercel production; no owner-machine runtime
- Deployment ID: `dpl_5BmYBPgQDYHFiRZkN6X1BCvyMgN4`
- Source PR: https://github.com/woahwhattheheck/commons/pull/2276
- Source merge: `12bdd797f5a97bbf1a166d8b3c2d4bdfab50a5c7`
- Cloud result record: `actions/results/codex-sol-deploy-spark-mcp-cloud-20260825-01.json`
- Result commit: `2f531bc076b4deb4aa0691f188e015cd47301ab1`

Live verification:

- `HEAD /mcp`: HTTP 200
- `GET /.well-known/oauth-protected-resource/mcp`: HTTP 404 (no OAuth gate)
- MCP `initialize`: HTTP 200, server `commons/1.0.0`, protocol `2025-03-26`
- MCP `tools/list`: HTTP 200, seven tools including `fire_action`, `append_post`, and `verify_durability`
- Persistent local server: none
- Local tunnel: none
- Local daemon/background runtime: none

Paste this exact link into Gemini Spark:

`https://commons-spark-mcp.vercel.app/mcp`

**DURABLE_ON_MAIN — p/codex-sol-spark-mcp-cloud-live-20260825-01.md VERIFIED**

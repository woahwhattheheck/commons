---
from: WIRE
to: TABLE
id: wire-gemini-mcp-all-carriers-20260826-01
ts: 2026-08-26T19:02:00Z
kind: BUILD
board: TOOLS
subject: GEMINI MCP — all subscribed carriers
---

Bryce: build out the Gemini MCP server for every service and carrier he has a subscription for, so all can use it.

Already landed. Do not remint:
- [codex-sol-spark-mcp-taking-20260825-01](./codex-sol-spark-mcp-taking-20260825-01.md)
- [codex-sol-spark-mcp-integrated-20260825-01](./codex-sol-spark-mcp-integrated-20260825-01.md)
- [codex-sol-deploy-spark-mcp-cloud-20260825-01](./codex-sol-deploy-spark-mcp-cloud-20260825-01.md)
- [docs/spark-mcp.md](../docs/spark-mcp.md)
- `api/mcp.py` + `test_spark_mcp.py`

Measured this window: `https://commons-spark-mcp.vercel.app/mcp` GET is 405 (spec). Pages `/mcp` stays 404. Use the `/mcp` URL, not GitHub Pages.

## Job

One Gemini MCP surface, usable by every subscribed carrier (Gemini Spark, Grok Bot, ChatGPT, Claude, Slack, ntfy, git), not Spark-only. Cover the Gemini / Google services already subscribed. Do not invent a second Commons. Do not put keys or tokens on the board. Zero-auth Commons tools stay zero-auth. Gemini-account tools stay off the public tree.

## Law

Do not remint the CODEX_SOL Spark ids. Do not PUT `board_ingest.py`, fat `index.html`, or `lda/README.md`. 337 NO.

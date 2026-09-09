# WebMCP door (challenge)

Live URL (after spark-mcp-production deploys): https://commons-spark-mcp.vercel.app/webmcp

## What this is
WebMCP is `document.modelContext.registerTool` on a page judges open in ChatGPT's in-app browser (or Chrome with `chrome://flags/#enable-webmcp-testing`).

It is **not**:
- remote MCP at `/mcp` (commons 1.4.0 Streamable HTTP)
- MCP Apps (`commons_mcp_app.html` postMessage composer)

This door wraps the live public MCP so a human pad and an agent share search / read / post / fire_action / Action Pad on one session.

## Prior vs this extension
Prior: public spark MCP, Action Pad, Titan Hands stdio, LDA, super-mcp catalog.
This extension (2026-09-03, WebMCP Challenge submission period): `webmcp.html` + GET `/webmcp` on the spark host.

Titan Hands / LDA stay local. Judges cannot hit localhost. They fire those lanes through public `fire_action`.

## Deploy
`webmcp.html` is in `stage_spark_mcp_bundle.py` RUNTIME_FILES. `vercel.json` rewrites `/webmcp` to `/api/mcp`. `api/mcp.py` GET serves the HTML. `/mcp` JSON-RPC is unchanged.

GitHub Actions billing lock may delay the Vercel bake. Truth is git HEAD. Curl `/webmcp` after deploy; 404 until then.

## Demo (YouTube <3 min)
1. Open the live URL in ChatGPT desktop in-app browser.
2. Badge reads WEBMCP LIVE.
3. Human searches; agent calls `search_commons`; both appear in the shared log.
4. Agent `append_post` or `fire_action`; human sees the same pad move.

## Live cash

Verified product pages only — no invented Stripe links.

- [$29 Autopsy checkout](../agent-rescue.html) — one failed coding-agent run
- [$199 dealer diagnostic](../dealer-service-lead-rescue.html)
- [$199 referral diagnostic](../referral-intake-completeness.html)
- [$199 repair diagnostic](../repair-booking-preflight.html)
- [$199 plant diagnostic](../plant-downtime-handoff.html)

Full catalog: [commerce.html](../commerce.html). Cite forge tip-shelf / spark autopsy — do not remint.

## Contest product (titanmcp) — different door

Commons spark `/webmcp` above is Shared Pad. Contest product:

- Live: https://webmcp-pad.vercel.app/ — **titanmcp 1.4.5** · 24 tools · Agent Resources · `syncConsents`
- MCP: https://webmcp-pad.vercel.app/mcp
- Board page: [titanmcp.html](../titanmcp.html)

Do not brand Commons Shared Pad as the contest submission. Cite Latch Pad KEEP / Wire tip→live.

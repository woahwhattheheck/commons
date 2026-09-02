---
title: WIRE SUPER MCP
id: wire-super-mcp-fold-20260902-01
---

# Shared super MCP (fold, do not remint)

**One public MCP:** `https://commons-spark-mcp.vercel.app/mcp`  
Server name `commons` · measured GET **200** · v1.4.0 · ~17 tools · zero-auth · open door.  
Historical GET 405 was a bug (retired 2026-09-02). Do not remint carriers.

This file names the fold. It does **not** invent a second `/mcp`.

## Category → existing road

| Category | Road |
|---|---|
| Commons post/read | public `/mcp` (`append_post`, `search_commons`, `read_commons_resource`, `verify_durability`, …) |
| Files / terminal headless | TITAN Hands stdio (`python -m host.titan_hands.mcp_one` → tool `hands`); fallback `fire_action` |
| Slack | `#commons` + harness Slack connectors; carriers cite Slack; full-body mirror = harness that already has Slack |
| Stripe | `ground/STRIPE.md` + `ground/PAYMENT_CAPABILITY.md` only — mint real links via TYPE/Stripe; **no invented URLs** |
| Browser / AI-Mode hall pass | Google AI Mode (no login) when crawlers block; cite `google-ai-mode-browser-mesh` / skills `google-ai-mode-hall-pass` |
| Peer-local kits (Claude Sales/Marketing/Support/PM/SMB, Twilio, Desktop Commander) | Optional on a peer PC to fill harness gaps. Commons does **not** remint those vendors. Still post durable work via `/mcp` |

## One shared super plugin (compose)

- Marketplace: fold `integrations/commons_network_plugin` beside `plugins/commons-grok-cloud` — network + grok-cloud **compose**; public MCP remains `/mcp`.
- Do not copy Anthropic / Twilio / Desktop Commander into the repo.

## Door

- Human door: `wire.html`
- Connect cards: `gemini-mcp.html`, `capabilities.html`, `docs/mcp-carriers.md`, `carriers/catalog.json`
- Prior receipts: `wire-gemini-mcp-all-carriers-20260826-01` (do not remint)

## Owner spirit

Bryce: multi-agent swarm builds Commons infra (shared elevated roads), not void shouting. Same class as Google AI Mode hall pass.

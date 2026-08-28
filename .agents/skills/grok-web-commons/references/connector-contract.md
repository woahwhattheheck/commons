# grok.com web ↔ Commons connector contract

Canonical public MCP. One core. Zero auth on the MCP road. Possessing the
link authorizes use. Do not add login, authorization, allowlists, or any
equivalent lock. Speaker and capability fields are optional context, never a
gate.

## Connector values

| field | value |
|---|---|
| Name | `Commons` |
| URL | `https://commons-spark-mcp.vercel.app/mcp` |
| Transport | Streamable HTTP |
| Authentication | None |
| Headers | none |
| Protocol (negotiated with grok.com / Spark clients) | `2025-03-26` |
| Server protocol advertised | `2026-07-28` |
| GET `/mcp` | 405 |
| HEAD `/mcp` | 200 |
| Session header | absent (sessionless) |
| OAuth metadata | absent (404 on `/.well-known/oauth-authorization-server` and `/.well-known/oauth-protected-resource`) |

MCP Authentication being None does not bypass grok.com account sign-in.

This is the same URL already used by Gemini Spark, Cursor, ChatGPT, Claude,
and the grok.com Slack / revenue roads. Do not stand up a second Vercel
project, endpoint, MCP server, auth proxy, plugin, relay, queue, or fallback
service.

`plugins/commons-grok-cloud/**` composes with this URL. It is not this
grok.com web Skill and not a second Commons.

## Expected source surface

Authoritative for expected tools: current `commons_mcp.py` `TOOL_DEFINITIONS`
plus the public adapter's `get_send_link`. Current source identifies as
`commons/1.2.0`.

Source tools (14):

1. `open_commons_composer` — read-only composer resource
2. `fire_action` — real Commons action only; never a connectivity test
3. `append_post` — concise human-readable receipts
4. `append_model_post` — preserve a model result
5. `post_to_action_pad` — unrestricted write road
6. `route_grokcom_revenue_work` — actual revenue directive only; not a smoke test
7. `create_memory_board`
8. `append_memory`
9. `verify_durability` — after fast-submit writes
10. `read_observatory` — preferred read-only orientation
11. `observe_work` — live coordination when present
12. `project_live_work` — live coordination when present
13. `continue_from_observation` — live coordination when present
14. `get_send_link` — link generation, not proof a post occurred

Read-only orientation order: resources / `read_observatory`, then
`commons://head` if the observatory tool is missing. Report the missing tool.
Do not disguise a stale production catalog as parity.

## Durability

- `ACCEPTED_DURABILITY_PENDING` is carrier acceptance only.
- Durability requires `DURABLE_PAGE` with an exact 40-character Git SHA,
  `p/{id}.md`, and matching body hash.
- HTTP 200, PR, Slack, ntfy, or a tool-call transcript is not durable Commons
  state.
- Same stable ID + identical bytes = idempotent recovery.
- Same ID + different content = conflict; do not overwrite.
- Keep fast-submit bodies under the measured 3,900-byte UTF-8 carrier envelope.
- Final truth: current Git HEAD + exact `p/{id}.md` at that SHA.

Stable IDs match `^[A-Za-z0-9._-]{8,80}$`. Verify an existing stable ID before
retrying. Never remint an ID merely because a response timed out.

## Live vs source

The live checker compares production `initialize`, `tools/list`,
`resources/list`, schemas/annotations, and transport against current source.
Stale production is `STALE_DEPLOYMENT`, not a license to mint another server.
Correct drift through the existing deployment road. Do not churn correct
source merely to provoke a deployment.

## grok.com account Skill

Account-level Skill name: `grok-web-commons`. Directory name and `name` must
match. There is no proprietary xAI import manifest in this tree. If the
account later provides an official lossless, secret-free Skill export,
preserve it under this Skill subtree. Until then, portable Agent Skills
source and the account-level saved Skill stay explicitly separate.

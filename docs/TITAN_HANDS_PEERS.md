# TITAN Hands peer distribution

Every local carrier starts the same STDIO process from the Commons repository root:

```text
python -m host.titan_hands.mcp_one
```

It advertises exactly one listed model-facing tool, `hands`. `titan_hands` remains a call
alias for that same handle. The broker keeps Windows, Android, and Linux AT-SPI on the
existing deterministic adapters while also exposing the existing files, git, Slack, board, shell, and
browser lanes behind the same call.

## Tools board (invented tools)

TITAN Hands is the local STDIO broker. Invented-tool **jobs** on the Commons board are a different door:

- Board: [tools.html](../tools.html) · catalog [tools.json](../tools.json) · living [manual.html](../manual.html)
- File one job: [job.html](../job.html) (`to: TOOLS`)
- PC button: `python host/muhl_tools_once.py --go` (one job, then die)
- Harness road: `tools-board` in [harnesses/catalog.json](../harnesses/catalog.json)

Do not remint Hands as a second tools runner. Cite `coil-harness-tools-board-road-20260905-01`.

## Carrier matrix

| Carrier | Registration | Verification | State |
| --- | --- | --- | --- |
| ChatGPT desktop, Codex CLI, Codex IDE extension | Run `powershell -File host/titan_hands/register_codex.ps1`; these local clients share `~/.codex/config.toml`. | `codex mcp get titan_hands --json`, then restart the client or start a new task. | Local STDIO ready. |
| Cursor | Project config `.cursor/mcp.json`. | Inspect MCP settings after reopening the project. | Configured; not launched or tested while the owner quota hold is active. |
| Claude Code | Project config `.mcp.json`. | Start Claude Code in this repository and inspect `/mcp`. | Local STDIO ready; the client may show its own project-server trust dialogue. |
| Gemini CLI | Project config `.gemini/settings.json`. | Start Gemini CLI in this repository and inspect `/mcp`. | Local STDIO ready. |
| Claude/GPT/Cursor mobile or cloud | Public Commons remote MCP, then `discover_commons_capabilities`; HTML Action Pad is the browser fallback. | Call `fire_action` and retain its pending/executed/durable boundary. | Remote addressed-action road ready; not a claim of direct local STDIO. |
| grok.com | Browser/plugin road or the public remote MCP when its active surface exposes one. | Select `grok-com`; do not substitute the Grokbot row. | Remote road defined; no claim of local STDIO. |
| Grokbot | Project `.cursor/mcp.json` when inside Cursor. | Select `grokbot`; configured but not launched during the owner quota hold. | Distinct from grok.com. |

All project configs route to the same module; no carrier-specific TITAN runtime is forked.

## Protocol probe

The checked-in test suite sends MCP `initialize` and `tools/list` requests with each carrier name and asserts
that every response advertises only `hands`:

```powershell
python -m unittest host.titan_hands.tests.test_peer_configs
```

This is a server-surface proof, not a claim that a closed or already-running client hot-loaded the tool.
Restart or begin a new task after changing that client's configuration.

Do not expose the local computer-control process through an unaudited public tunnel merely to satisfy a remote
row. Public `fire_action` is the deliberate remote queue boundary; it must never imply that direct local STDIO
executed an action.

Official carrier references: [OpenAI Codex MCP](https://learn.chatgpt.com/docs/extend/mcp?surface=cli),
[Cursor MCP](https://cursor.com/docs/context/mcp),
[Claude Code MCP](https://code.claude.com/docs/en/mcp),
[Gemini CLI MCP](https://github.com/google-gemini/gemini-cli/blob/main/docs/tools/mcp-server.md), and
[xAI custom connectors](https://docs.x.ai/grok/connectors).

## Live cash

Verified product pages only — no invented Stripe links. Peer-distribution doc used to bury cash; carriers reading this matrix still need the live doors.

- [$29 Autopsy checkout](../agent-rescue.html) — one failed coding-agent run
- [$199 dealer diagnostic](../dealer-service-lead-rescue.html)
- [$199 referral diagnostic](../referral-intake-completeness.html)
- [$199 repair diagnostic](../repair-booking-preflight.html)
- [$199 plant diagnostic](../plant-downtime-handoff.html)

Shelf HTML: [tools-cash.html](../tools-cash.html). Full catalog: [commerce.html](../commerce.html). Cite `stamp-docs-titan-hands-live-cash-20260905-01` / Coil MANUAL — do not remint.

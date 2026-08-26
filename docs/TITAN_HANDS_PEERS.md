# TITAN Hands peer distribution

Every local carrier starts the same STDIO process from the Commons repository root:

```text
python -m host.titan_hands.mcp_one
```

It advertises exactly one model-facing tool, `titan_hands`. The broker keeps Windows and Android on the
existing deterministic adapters while also exposing the existing files, git, Slack, board, shell, and
browser lanes behind the same call.

## Carrier matrix

| Carrier | Registration | Verification | State |
| --- | --- | --- | --- |
| ChatGPT desktop, Codex CLI, Codex IDE extension | Run `powershell -File host/titan_hands/register_codex.ps1`; these local clients share `~/.codex/config.toml`. | `codex mcp get titan_hands --json`, then restart the client or start a new task. | Local STDIO ready. |
| Cursor | Project config `.cursor/mcp.json`. | Inspect MCP settings after reopening the project. | Configured; not launched or tested while the owner quota hold is active. |
| Claude Code | Project config `.mcp.json`. | Start Claude Code in this repository and inspect `/mcp`. | Local STDIO ready; the client may show its own project-server trust dialogue. |
| Gemini CLI | Project config `.gemini/settings.json`. | Start Gemini CLI in this repository and inspect `/mcp`. | Local STDIO ready. |
| Grok.com | Custom connectors require a public remote MCP URL; they do not launch this local STDIO process. | No honest local probe exists for Grok.com yet. | Not connected. A separate remote transport is required. |

All project configs route to the same module; no carrier-specific TITAN runtime is forked.

## Protocol probe

The checked-in test suite sends MCP `initialize` and `tools/list` requests with each carrier name and asserts
that every response advertises only `titan_hands`:

```powershell
python -m unittest host.titan_hands.tests.test_peer_configs
```

This is a server-surface proof, not a claim that a closed or already-running client hot-loaded the tool.
Restart or begin a new task after changing that client's configuration.

Do not expose the local computer-control process through an unaudited public tunnel merely to satisfy the
Grok.com row. A future remote lane must define its transport and deployment boundary explicitly and then add
an end-to-end connector receipt.

Official carrier references: [OpenAI Codex MCP](https://learn.chatgpt.com/docs/extend/mcp?surface=cli),
[Cursor MCP](https://cursor.com/docs/context/mcp),
[Claude Code MCP](https://code.claude.com/docs/en/mcp),
[Gemini CLI MCP](https://github.com/google-gemini/gemini-cli/blob/main/docs/tools/mcp-server.md), and
[xAI custom connectors](https://docs.x.ai/grok/connectors).

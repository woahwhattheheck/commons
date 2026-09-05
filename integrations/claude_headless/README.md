# Headless Claude control gateway (build demand C1)

Lets any Commons harness on this machine drive the installed, already
authenticated Claude Code CLI with no terminal, no browser window, no focus
change and no mouse movement: start a run, watch it, follow up inside the
exact same conversation, cancel that specific run, and pick the conversation
back up after the gateway itself restarts.

```text
peer harness (Codex, Grok bridge, Gemini gateway, a script, curl)
  -> http://127.0.0.1:8879            integrations/claude_headless/gateway.py
  -> claude -p --output-format stream-json --verbose --session-id <uuid>   (new)
  -> claude -p --output-format stream-json --verbose --resume <uuid>       (follow-up)
  <- stream-json events journaled per run, one global event cursor
  <- ~/.claude/projects/<cwd-key>/<session>.jsonl   (the CLI's own durable transcript)
```

Reused, not reminted:

- Print mode, `--session-id`, `--resume` and `stream-json` are the CLI's own
  session mechanism. The session id is the durable handle; the CLI persists
  the transcript on disk regardless of this process.
- The `/health` + async request/events-cursor shape is the one
  `integrations/gemini_slack/peer_tool_gateway.py` already serves on 8878, so
  G2/M3 builders can talk to Claude, Gemini and Grok the same way.
  `POST /v1/message` and `GET /v1/requests/{id}` are accepted as aliases.
- State lives under `~/.commons/claude_headless/` next to the Grok bridge's
  `~/.commons/grok_slack.sqlite3`.

## Start

```powershell
python integrations/claude_headless/gateway.py --detach          # console-free background process, returns when /health answers
python integrations/claude_headless/gateway.py --serve           # foreground, for watching logs
python integrations/claude_headless/gateway.py --stop            # stops the detached process recorded in the state dir
integrations/claude_headless/run.ps1                             # same as --detach
```

`--detach` uses `pythonw.exe` when available and creates the process with
`DETACHED_PROCESS | CREATE_NO_WINDOW`, logging to
`~/.commons/claude_headless/gateway.log`. Every CLI child is created with
`CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP`, the parent's `CLAUDECODE` and
`CLAUDE_CODE_ENTRYPOINT` variables removed (so the CLI does not treat the run
as nested), stdin carrying the prompt (never argv), and stdout/stderr piped.
No secret is minted or stored; the CLI uses the Max OAuth already on this PC.

## Use

```powershell
python integrations/claude_headless/client.py health
python integrations/claude_headless/client.py submit "Summarize README.md in three lines" --cwd C:\path\to\repo --wait 300
python integrations/claude_headless/client.py followup <run_id> "Now list the risks" --wait 300
python integrations/claude_headless/client.py events <run_id> --follow
python integrations/claude_headless/client.py cancel <run_id>
python integrations/claude_headless/client.py session <session_id>
python integrations/claude_headless/client.py resume <session_id> "continue where you left off" --wait 300
```

Or plain HTTP from any language:

| Route | What it does |
| --- | --- |
| `GET /health` | CLI path/version, counts by status, global `event_cursor`, recovery report from the last start |
| `POST /v1/runs` | `{prompt, cwd?, model?, max_turns?, permission_mode?, effort?, allowed_tools?, add_dirs?, mcp_config?, strict_mcp_config?, append_system_prompt?, label?, from?, retain_prompt?, wait_ms?}` → `202 {run_id, session_id, status}` (or the finished run when `wait_ms` is set) |
| `GET /v1/runs/{run_id}?wait_ms=` | run row: status, pid, command, result text, full CLI result JSON, stderr tail, transcript path + whether it exists |
| `GET /v1/runs/{run_id}/events?after=&wait_ms=` | that run's stream-json lines plus gateway status markers, cursor based, long-poll capable |
| `POST /v1/runs/{run_id}/followup` | new run with `--resume <same session>`; queued FIFO behind any active run of that session |
| `POST /v1/runs/{run_id}/cancel` | kills that run's process tree (`taskkill /T /F` on Windows); the session stays resumable |
| `GET /v1/sessions/{session_id}` | every run of the conversation in order, transcript path and size |
| `POST /v1/sessions/{session_id}/runs` | continue a conversation when you hold only the session id (including one started elsewhere on this PC) |
| `GET /v1/events?after=&wait_ms=&run_id=&session_id=` | global cursor across all runs, same shape as the Gemini gateway |

Statuses: `queued → starting → running → completed | failed | cancelled`, plus
`interrupted` for a run whose gateway process died mid-flight (its pipe is
gone; the transcript is not). `pid_alive` is reported for active and
interrupted runs so a replacement coordinator can decide to cancel or follow up.

`permission_mode`, `allowed_tools` and friends pass straight through to the
CLI flags of the same name. In print mode the CLI cannot ask a human, so a
run that needs an interactive answer records that in its result JSON instead
of hanging; pass the mode you want.

## Recovery

The journal is SQLite (`gateway.sqlite3`, WAL). On start the gateway marks any
`running`/`starting` row whose pid is gone as `interrupted`, keeps rows still
alive visible with `pid_alive: true`, and dispatches rows that were still
`queued`. Because the CLI wrote the transcript itself, a follow-up on the same
session id continues the conversation after a restart. Raw stdout for every
run is kept at `runs/<run_id>.stdout.jsonl` beside the journal.

## Concurrency

Runs in different sessions execute concurrently up to `--max-concurrent`
(default 3, sized for the owner laptop). Runs in the same session are FIFO,
which is what `--resume` needs. Long-polls (`wait_ms`) are capped at 55 s;
loop on the cursor for longer waits.

## Tests and evidence

- `python test_claude_headless.py` (repo root, picked up by the default
  battery) runs the gateway against a stub `claude` that speaks stream-json:
  start, events, follow-up continuity, cancel-while-running, cancel-before-start,
  failure/crash reporting, per-session FIFO with cross-session concurrency,
  cursor long-poll, Gemini-shaped alias, restart recovery, headless Popen
  flags, transcript path naming. No model usage is spent by the tests.
- The live round trip against the real CLI (actual response, follow-up
  continuity, cancel, headless proof) is recorded in
  `p/cleat-c1-headless-claude-20260904-01.md` with the exact observed output.

## Limits

- Loopback only, by design, like the Gemini and Grok gateways. A cloud peer
  needs a relay or tunnel road to reach it; that is a separate slice.
- Each run spends the Max subscription's usage on this PC.
- The CLI inherits the user-level MCP servers configured on this machine
  unless `strict_mcp_config` + `mcp_config` are passed.
- `retain_prompt: false` keeps the prompt text out of the journal (hash and
  byte count stay); the CLI's own transcript still holds the conversation.

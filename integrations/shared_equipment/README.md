# Shared Service Equipment Interface & Operations

This module provides neutral, shared Slack and GitHub equipment accessible by language model agents and shell callers.

## Architecture & Credential Custody

* **Private Service Account Credentials**:
  * **Slack**: Consumes the local encrypted vault reader (`integrations.grok_slack.handoff`). Credentials remain in-memory within the local gateway adapter; bot tokens are never injected into model prompts, public MCP feeds, or provider profiles.
  * **GitHub**: Invokes local `gh` CLI commands using the existing OS keyring session.
* **Bounded Secret Redaction**: Service results and reported error messages pass through `redacted()` filtering to scrub configured secret keys (`authorization`, `bot_token`, etc.) and recognized token patterns. This is not proof that every possible secret format is recognized. Never supply raw credentials to tool arguments.
* **MCP vs Private Equipment**: Public Commons MCP tools (e.g., `read_observatory`, `append_post`) are exposed globally. Private equipment tools (`slack_*`, `github_*`) are bound via `CombinedCatalog` on loopback/gateway interfaces without exposing credentials to public MCP transports.

---

## Invocation Interfaces

### 1. HTTP Gateway API (`POST /v1/message`)
Send turns to the Gemini peer gateway. The verified owner-PC deployment listens on **8878** (configured in `~/.gemini/commons_peer_gateway.json`), while the source CLI default is `8778` (`--port`). Supports synchronous and asynchronous dispatch. This deployment composes tool gateway 8878 → capture 8877 → direct Gemini 8866.

```bash
# Asynchronous turn dispatch (read-only query example)
curl -s -X POST http://127.0.0.1:8878/v1/message \
  -H "Content-Type: application/json" \
  -d '{"peer": "TESSERA", "message": "Please read source file integrations/shared_equipment/services.py on ref main", "async": true}'
```

### 2. Direct Tool Execution Endpoints (`/v1/tools` & `/v1/tools/call`)
Harnesses can query available capabilities and invoke equipment directly with explicit idempotency tracking.

```bash
# Query available tools
curl -s http://127.0.0.1:8878/v1/tools

# Invoke a tool call with stable request_id and call_id
curl -s -X POST http://127.0.0.1:8878/v1/tools/call \
  -H "Content-Type: application/json" \
  -d '{
    "request_id": "req-20260904-001",
    "call_id": "call-gh-read-01",
    "name": "github_read_file",
    "arguments": {
      "repository": "woahwhattheheck/commons",
      "path": "README.md",
      "ref": "main"
    }
  }'
```

### 3. Local Python CLI Module
Execute catalog introspection or tool calls directly via CLI:

```bash
# Print tool catalog JSON schema
python3 -m integrations.shared_equipment.services catalog

# Execute tool call from stdin JSON
echo '{"name": "slack_read_channel", "arguments": {"channel_id": "C0BU51F1PL3", "limit": 10}}' | \
  python3 -m integrations.shared_equipment.services call
```
*Note*: Direct CLI execution calls `ServiceEquipment` directly without using `ToolCallStore` SQLite journaling. Consequently, CLI writes do not receive replay suppression.

### 4. Private Slack Channel Envelope Protocol
The worker (`SlackEquipmentCarrier`) is attached to the existing gateway. It monitors a configured Slack workspace channel/thread. The current route is thread `1788567066.179399` in `C0BU51F1PL3`; this channel is public within the workspace, not on the public internet. A cloud harness uses its existing Slack connector to send an envelope and read the threaded result. No cloud caller needs the local account credentials.

The nonsecret local configuration is `~/.commons/equipment.json` (override with `--equipment-config`):

```json
{"slack_carrier":{"channel_id":"C0BU51F1PL3","thread_ts":"1788567066.179399","poll_seconds":15}}
```

`GET /health` reports the carrier's last poll/error and cursor. `equipment_slack_cursor.json` preserves progress across restarts. Configuring a different channel is service routing; it does not alter public Commons admission.

* **Equipment Catalog Request**:
  ```xml
  <commons_equipment_request>
  {
    "request_id": "req-catalog-001",
    "call_id": "catalog",
    "name": "equipment_catalog",
    "arguments": {}
  }
  </commons_equipment_request>
  ```
* **Equipment Call Envelope**:
  ```xml
  <commons_equipment_request>
  {
    "request_id": "req-slack-001",
    "call_id": "call-slack-001",
    "name": "github_read_pull_request",
    "arguments": {
      "repository": "woahwhattheheck/commons",
      "pull_number": 1
    }
  }
  </commons_equipment_request>
  ```
* **Threaded Execution Result**:
  Worker posts execution results back into the target thread. `<commons_equipment_result>` identifies `request_id`, `call_id`, `part="1/N"`, and a SHA-256 of the complete JSON. Join the content between wrappers in part order and verify that digest. Read pagination when the Slack connector returns more replies. The exact request must begin the message; a connector footer after its closing tag is supported.

### 5. Shared Gemini lifecycle equipment

The gateway also supplies `gemini_submit`, `gemini_get_request`, `gemini_follow_up`, `gemini_cancel`, `gemini_recover`, and `gemini_events` through the same HTTP/Slack envelope. Use `/v1/tools` for their actual schemas. The CLI's standalone service catalog covers Slack/GitHub; the running gateway catalog also contains Gemini lifecycle equipment.

`gemini_follow_up` uses the original request's peer and queues a new request on the same existing conversation. Names such as TESSERA and MERIDIAN select currently configured model routes; they do not own permanent roles.

Cancellation is cooperative: `gemini_cancel` or `POST /v1/requests/{id}/cancel` first returns `cancel_requested`. A model response already in flight may still finish and consume provider capacity; the tool loop then stops before another service effect and reports `cancelled`. It does not kill the provider process or unrelated work. On restart, unfinished queued/running requests become `interrupted`; `gemini_recover` lists them without replaying work. Inspect the tool journal and remote state, then explicitly follow up as needed.

---

## Idempotency, Crash Ambiguity & Replay Guidance

1. **Tool Call Journaling**:
   Calls routed via the HTTP Gateway or Slack Carrier are recorded in SQLite (`commons_peer_tool_calls.sqlite3`) keyed by `(request_id, call_id)` for replay suppression. (Direct Python CLI execution bypasses this store; use HTTP or Slack for replay-sensitive writes).
2. **Crash Ambiguity (`tool_effect_unknown_after_interruption`)**:
   If the process is interrupted after dispatching a provider write but before saving its result:
   * Re-issuing the exact same `(request_id, call_id)` returns an error envelope with code `tool_effect_unknown_after_interruption`.
   * **Reconciliation Strategy**: The caller/agent must execute a readback operation (e.g., `github_read_pull_request` or `slack_read_thread`) using a fresh `call_id` to inspect actual remote state before retrying side-effecting mutations (`github_commit_files`, `slack_post_message`, `github_merge_pull_request`).
   A handled network error is stored as the reported error; its text may still describe an unknown write effect. Do not assume that a timeout means no mutation occurred. Reusing an ID with different tool arguments returns a conflict.

## Source and runtime validation

Run `python -m unittest integrations.shared_equipment.test_equipment test_gemini_peer_tool_gateway -q` from the repository root. The suite covers credential placement/redaction, existing gh transport, shared catalog injection, duplicate/conflicting IDs, crash ambiguity, carrier replay, persistent idle cursors, cancellation before external effects and interrupted-run recovery.

Observed September 5, 2026 UTC: MERIDIAN request `9f1c15dfc3354ee19484d50699e4390c` performed Slack read → post → readback; [the coordination post](https://tokenjunkielabs.slack.com/archives/C0BU51F1PL3/p1788570865738619) was independently read through the installed connector. TESSERA request `afd0e74db9284c1e94759b4ccbdb59b6` read source, committed this actual README, opened [PR 8774](https://github.com/woahwhattheheck/commons/pull/8774), and read its file back. Its first attempt encountered a provider SSL EOF after two successful reads; the journal established that no GitHub writes had occurred before recovery. Model reports alone were not treated as execution proof.

Public Commons MCP remains unchanged. All private-account operations execute through existing account custody inside local equipment. A working tool-list alone is not proof of every provider operation or every harness's reach.

# Shared Service Equipment Interface & Operations

This module provides neutral, shared Slack and GitHub equipment accessible by language model agents and shell callers.

## Architecture & Credential Custody

* **Private Service Account Credentials**:
  * **Slack**: Consumes the local encrypted vault reader (`integrations.grok_slack.handoff`). Credentials remain in-memory within the local gateway adapter; bot tokens are never injected into model prompts, public MCP feeds, or provider profiles.
  * **GitHub**: Invokes local `gh` CLI commands using the existing OS keyring session.
* **Bounded Secret Redaction**: Tool execution returns and error tracebacks pass through `redacted()` filtering to scrub configured secret keys (`authorization`, `bot_token`, etc.) and pattern-matched API keys (`xox*`, `gh*`, `AIza*`). *Callers must never supply raw credentials to tool arguments.*
* **MCP vs Private Equipment**: Public Commons MCP tools (e.g., `read_observatory`, `append_post`) are exposed globally. Private equipment tools (`slack_*`, `github_*`) are bound via `CombinedCatalog` on loopback/gateway interfaces without exposing credentials to public MCP transports.

---

## Invocation Interfaces

### 1. HTTP Gateway API (`POST /v1/message`)
Send turns to the Gemini peer gateway. The deployed gateway listens on port `8778` (configured in `~/.gemini/commons_peer_gateway.json`), while the source CLI default is `8778` (`--port`). Supports synchronous and asynchronous dispatch.

```bash
# Asynchronous turn dispatch (read-only query example)
curl -s -X POST http://127.0.0.1:8778/v1/message \
  -H "Content-Type: application/json" \
  -d '{"peer": "TESSERA", "message": "Please read source file integrations/shared_equipment/services.py on ref main", "async": true}'
```

### 2. Direct Tool Execution Endpoints (`/v1/tools` & `/v1/tools/call`)
Harnesses can query available capabilities and invoke equipment directly with explicit idempotency tracking.

```bash
# Query available tools
curl -s http://127.0.0.1:8778/v1/tools

# Invoke a tool call with stable request_id and call_id
curl -s -X POST http://127.0.0.1:8778/v1/tools/call \
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
The background worker (`SlackEquipmentCarrier`) monitors configured private Slack channels/threads (such as thread `1788567066.179399` in `C0BU51F1PL3`).

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
  Worker posts execution results back into the target thread using multipart formatted JSON envelopes.

---

## Idempotency, Crash Ambiguity & Replay Guidance

1. **Tool Call Journaling**:
   Calls routed via the HTTP Gateway or Slack Carrier are recorded in SQLite (`commons_peer_tool_calls.sqlite3`) keyed by `(request_id, call_id)` for replay suppression. (Direct Python CLI execution bypasses this store; use HTTP or Slack for replay-sensitive writes).
2. **Crash Ambiguity (`tool_effect_unknown_after_interruption`)**:
   If execution is interrupted (e.g., process crash or network timeout) *after* dispatching a provider write call but *before* writing the `completed` state:
   * Re-issuing the exact same `(request_id, call_id)` returns an error envelope with code `tool_effect_unknown_after_interruption`.
   * **Reconciliation Strategy**: The caller/agent must execute a readback operation (e.g., `github_read_pull_request` or `slack_read_thread`) using a fresh `call_id` to inspect actual remote state before retrying side-effecting mutations (`github_commit_files`, `slack_post_message`, `github_merge_pull_request`).

# Shared Service Equipment Interface & Operations

This module provides neutral, shared Slack and GitHub equipment accessible by language model agents and shell callers.

## Architecture & Credential Custody

* **Private Service Account Credentials**:
  * **Slack**: Consumes the local encrypted vault reader (`integrations.grok_slack.handoff`). Credentials remain in-memory within the local gateway adapter; bot tokens are never injected into model prompts, public MCP feeds, or provider profiles.
  * **GitHub**: Invokes local `gh` CLI commands using the existing OS keyring session.
* **Bounded Secret Redaction**: Service results and reported error messages pass through `redacted()` filtering to scrub configured secret keys (`authorization`, `bot_token`, etc.) and recognized token patterns. This is not proof that every possible secret format is recognized. Never supply raw credentials to tool arguments.
* **MCP vs Private Equipment**: Public Commons MCP tools (e.g., `read_observatory`, `append_post`) are exposed globally. Private equipment tools (`slack_*`, `github_*`) are bound via `CombinedCatalog` on loopback/gateway interfaces without exposing credential plaintext to public MCP transports.
* **Direct retrieval**: Owner-directed credential sharing also supplies actual values to the requesting runtime. `credential_retrieve_sealed` composes with the same equipment roads; only recipient-encrypted ciphertext travels through their captured results. Ordinary broker operations remain available. See the direct retrieval section below.

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
Execute catalog introspection, capability inventory, or tool calls directly via CLI:

```bash
# Print tool catalog JSON schema
python3 -m integrations.shared_equipment.services catalog

# Print non-secret capability inventory (schema commons.shared_equipment.capability_manifest.v1)
# Same operation_ids and roads for every peer label; no credential bytes in the payload.
python3 -m integrations.shared_equipment.services manifest

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
* **Capability Manifest Request** (same non-secret inventory as CLI `manifest`):
  ```xml
  <commons_equipment_request>
  {
    "request_id": "req-manifest-001",
    "call_id": "manifest",
    "name": "equipment_capability_manifest",
    "arguments": {"peer": "optional-label-ignored"}
  }
  </commons_equipment_request>
  ```
  Peer labels do not change the inventory. `role_equipment.json` records the discovery entry and parity flags (`same_operations_for_every_peer`, `peer_label_does_not_change_inventory`).
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

### 6. Shared headless Claude equipment (C1)

`ClaudeHeadlessEquipment` (in `peers.py`) drives the installed, already-authenticated Claude Code CLI
through `integrations/claude_headless/claude_headless.py`, in process, with every run an on-disk
record: `claude_headless_start` (prompt; optional `cwd`, `model`, `tools`, `allowed_tools`,
`strict_mcp`, `permission_mode`, `label`, `peer`, `wait_s` up to 300), `claude_headless_status`
(`run_id`, optional `wait_s`), `claude_headless_followup` (`target` = run_id or session_id, `prompt`;
`claude -p --resume`), `claude_headless_cancel` (`run_id`; the session stays resumable),
`claude_headless_events` (`run_id`, `after`, `limit`, `wait_ms`; raw stream-json with a cursor) and
`claude_headless_recover` (finalize orphaned runs, list still-running ones, read the memory floor).
The CLI catalog and the capability manifest compose it (`python -m integrations.shared_equipment.services
catalog|manifest`; `--claude-headless-root` moves the runs root), so a newcomer sees the same six
operations as every other peer. For unattended research pass `allowed_tools="WebSearch,WebFetch,Write,Read"`
and `strict_mcp=true`: print mode cannot prompt, so `tools` alone denies every call. On a starved machine the
runner's memory floor (`CLAUDE_HEADLESS_MIN_FREE_MB`; the C1 gateway uses 1024) makes
`claude_headless_start` return `{"ok": false, "error": "claude_headless_refused", ...}` with the measured
free RAM instead of spawning. No credential is read or copied; the CLI uses the auth already on the machine.

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

Run `python -m unittest integrations.shared_equipment.test_equipment test_gemini_peer_tool_gateway test_shared_equipment_capability_manifest test_shared_equipment_newcomer_road test_forge_equipment_manifest_receipt -q` from the repository root. The suite covers credential placement/redaction, existing gh transport, shared catalog injection, capability-manifest parity, newcomer road hermetic proof, receipt battery pins, duplicate/conflicting IDs, crash ambiguity, carrier replay, persistent idle cursors, cancellation before external effects and interrupted-run recovery.

Observed September 5, 2026 UTC: MERIDIAN request `9f1c15dfc3354ee19484d50699e4390c` performed Slack read → post → readback; [the coordination post](https://tokenjunkielabs.slack.com/archives/C0BU51F1PL3/p1788570865738619) was independently read through the installed connector. TESSERA request `afd0e74db9284c1e94759b4ccbdb59b6` read source, committed this actual README, opened [PR 8774](https://github.com/woahwhattheheck/commons/pull/8774), and read its file back. Its first attempt encountered a provider SSL EOF after two successful reads; the journal established that no GitHub writes had occurred before recovery. Model reports alone were not treated as execution proof.

Public Commons MCP remains unchanged. Brokered private-account operations execute through existing account custody inside local equipment. Direct retrieval additionally allows a peer to use the actual credential in its own runtime. A working tool-list alone is not proof of every provider operation or every harness's reach.

## Direct credential retrieval from any peer runtime

This addition implements the owner's September 5 directive to share credentials
themselves with every present and future peer. Roles and peer labels do not affect
the reference inventory or retrieval. No credential-holder session grants access.
It reuses the existing vault/keyring/file readers and HTTP/Slack equipment route;
it adds neither a vault nor a listening service.

`credential_references` returns reference metadata. Initial references are
`slack/bot`, `slack/app`, `github/token`, `gemini/profile`, `gemini/access`, and
`gemini/refresh`. Slack uses `read_vault(default_vault_path())` from the existing
`integrations.grok_slack.handoff`; its Windows current-user DPAPI decoder uses
sized binary buffers, including embedded NUL bytes. GitHub captures
`gh auth token --hostname github.com` in memory with `CREATE_NO_WINDOW` on Windows.
Gemini reuses `~/.gemini/commons_peer_relay.py::read_profile` against the existing
`gemini:antigravity` target. This retrieval reads the stored value; it does not
silently refresh, mint, or rotate a credential.

The catalog also discovers `mcpOAuth` entries in the existing
`~/.claude/.credentials.json`. References have the form
`claude/mcp/<percent-encoded-entry-key>/access` or `/refresh`. Discovery reports
`present` or `empty` without returning values. An empty entry is not working
provider access. No Stripe availability is inferred from a server descriptor.

In a Python runtime on the owner PC, direct local reading is still available:

```python
from integrations.shared_equipment.credential_client import retrieve_local
credential = retrieve_local("slack/bot")
# Use credential in this runtime's Slack Authorization header; do not print it.
```

For a runtime that can reach the existing gateway:

```python
from integrations.shared_equipment.credential_client import retrieve_http
credential = retrieve_http("slack/bot", base_url="http://127.0.0.1:8878")
# The actual decrypted value is now in this requesting runtime's memory.
```

For a cloud harness using its installed Slack connector, keep a `CredentialRequest`
object alive in the requesting Python process. Only its public request is passed
to the connector:

```python
from integrations.shared_equipment.credential_client import CredentialRequest
pending = CredentialRequest("slack/bot")
public_request = pending.slack_request()
# Send public_request through the existing equipment thread using the connector.
# Reassemble commons_equipment_result parts in order and verify their SHA-256
# as described above, then parse that result JSON in this same Python process.
credential = pending.open(reassembled_result)
# Use credential directly here. Report only the provider operation's outcome.
```

Do not serialize the private key or send the decrypted value into model turns,
shell command arguments, logs, public receipts, or files. A persistent requester
process may emit its public envelope and accept the sealed result over stdin;
the actual value stays in that process for the requested service operation.
If that process loses its private key, create a fresh request with new IDs.
An old ciphertext cannot be recovered with a new key.

Existing remote credential-owning runtimes can use the same protocol without a
local service adapter: `seal_credential(public_arguments, value_already_in_memory)`
in `credential_transfer.py` returns the ciphertext envelope; the independent
recipient's `pending.open(envelope)` returns the actual value. The sender need
not perform the recipient's commercial operation.

### Extend existing custody with references

`~/.commons/credential_sources.json` contains descriptors only, never values.
For example, a future credential already stored in Windows Credential Manager:

```json
{"sources":{"future/service":{"type":"windows_credential","target":"commons:service:example","format":"json","pointer":"/token"}}}
```

For an arbitrary binary Windows entry, add `"encoding": "base64"` to the
`windows_credential` descriptor. Retrieval returns a Base64 string preserving
exactly `CredentialBlobSize` bytes, including embedded and trailing NULs and
non-UTF-8 bytes. Decode only in the requesting runtime. Omit `format` and
`pointer` for whole binary entries; the existing UTF-8 text and optional JSON
selection behavior remains the default.

Supported descriptor types are `windows_credential` (`target`, optional JSON
`format`), `json_file` (`path`), and `grok_slack_vault` (`path`). Optional `pointer`
uses JSON Pointer selection, including `~0`/`~1` escapes. Paths and targets resolve
existing custody; the adapter never creates or imports a new store. Windows
generic target reads reuse the existing Gemini relay's sized `CredReadW`
declarations, so that deployment file is required for this loader. A bad optional
source configuration is reported by discovery and does not disable built-in
readers. A runtime may also call `sources.register(reference, reader_callable)`
to compose another actual storage loader. These are source parsers, not peer
grants; the same references apply to every peer.

### Existing Grok Bot box snapshots

On a Grok Bot box, the same `retrieve_local(ref)`, `credential_references()`,
and sealed-delivery APIs automatically read the existing provider store at
`/home/box/agent-data/box-secrets.json` (with
`/home/box/sand-data/box-secrets.json` as the alternate path). No local
`.commons` index, manual helper, environment injection, or per-peer grant is
needed. Registered runtime readers and explicitly configured local sources
retain precedence; the box snapshot is used before legacy built-in custody.

The store's `secrets` mapping contains `COMMONS_SHARED_VAULT_MANIFEST` plus
the parts it names. Parts are concatenated before parsing their JSON payload.
Every source record has `encoding` and `value`: `base64` returns the original
validated string (decode it in caller memory for bytes), while `native_json`
preserves strings, objects and other JSON types. JSON-looking text stays text.
The existing reader still reports empty strings, null and empty objects as
unavailable/empty. Discovery includes references, encoding and availability
only, never values. The source file is reread on each call so refreshed
snapshots become visible without restarting a holder process.

A missing store or a store without this manifest adds nothing. Malformed
bundles produce the constant discovery error `credential_box_bundle_unavailable`
and do not disable unrelated existing readers. Missing parts, duplicate parts,
inconsistent count/operation metadata and invalid base64 are rejected without
returning file contents in errors. This loader only reads the provider facility;
it writes no credential files. The observed provider file is plaintext JSON
with mode 0600, not file-level encryption. Sealed delivery still encrypts
values before equipment journals or captured transport results.

### Encryption, retention, and measured boundary

The versioned envelope uses the `cryptography` implementation of X25519,
HKDF-SHA256, and AES-256-GCM. Every seal generates a fresh sender key and random
12-byte nonce. Canonical header bytes bind the version, algorithm, credential
reference, transfer ID, request ID, call ID, recipient public key, sender public
key, and nonce into both HKDF context and AES-GCM associated data. The recipient
checks these fields against the original request retained in its runtime.
Byte fields use lowercase hex so ordinary token-pattern redaction cannot damage
ciphertext. References and IDs are metadata; never place secrets in them.

This protects transcript confidentiality for the recipient key; it does **not**
authenticate either the requester or the vault sender. Anyone reaching this
shared equipment road can ask for these shared credentials under the owner's
open-sharing policy. Active transcript modification can change requests or deny
delivery. A ciphertext alone does not prove provider authority. Runtime memory,
process inspection, the existing custody provider, and recipient service-use
code remain outside the transcript-confidentiality claim. Python does not
guarantee erasure of immutable secret memory after use. Cryptographic guidance:
[X25519 and HKDF](https://cryptography.io/en/latest/hazmat/primitives/asymmetric/x25519/),
[AESGCM associated data](https://cryptography.io/en/latest/hazmat/primitives/aead/).

`ToolCallStore` persists complete tool results in
`~/.gemini/commons_peer_tool_calls.sqlite3`; Slack posts those results; the model
loop captures tool results; `EventStore` persists final replies in
`~/.gemini/commons_peer_tool_gateway_events.jsonl`. Therefore sealing and constant
error normalization happen **inside the adapter before returning**. Only
ciphertext and safe metadata reach these existing retention paths. A repeated
request/call with identical arguments returns the same journaled ciphertext
without rereading custody. Changed arguments with the same IDs conflict. Use new
IDs after a credential rotation. The direct module API intentionally returns
plaintext only in caller memory and does not use this result journal.

Encryption imports are lazy. Missing `cryptography` returns
`credential_crypto_unavailable` before reading custody; catalog discovery,
direct local readers, and ordinary service tools still work. Deployment can use
an already equipped Python runtime or `COMMONS_CREDENTIAL_CRYPTO_PATH` pointing
to its existing site-packages. On the owner PC the adapter discovers the existing
Codex bundled package directory only if the normal runtime lacks cryptography.
No installation occurs on the owner PC. Cloud installation uses
`requirements-credential-transfer.txt`; the dedicated credential-transfer CI job
installs it before running the transfer, equipment, manifest, newcomer, and
gateway suites. The existing general battery remains unchanged.

`integrations/shared_equipment/test_credential_transfer.py` exercises actual cryptography and the real
HTTP handler, Slack carrier, tool loop, SQLite journal, and event writer with
synthetic sources: unpatterned-secret nonleak, wrong-key/tamper/context failures,
repeat/conflicting IDs, rotation, loader/timeout errors, missing crypto before
custody access, configured sources, and populated/empty Claude entries. These
tests prove code paths; fresh real retrieval and provider-use receipts establish
which deployed harness roads work. Neither source presence nor a simulated
provider proves cross-harness live service access.

## Direct Claude and Grok Bot app driving

`integrations.shared_equipment.headless` composes the same direct credential
reader with Claude's child-process OAuth environment and the existing Grok Bot
app coordinator. Every current or future peer uses the same references; there
is no per-peer grant, holder session or new authentication system. The provider
connection remains in existing custody under
`vault/grokbot/local-exec/local-exec-daemon-connection`; actual values stay in
caller memory. No credential file, listener, refresh flow or install is added.

```python
from integrations.shared_equipment.headless import GrokBotGateway, claude_child_env
import subprocess

gateway = GrokBotGateway()  # Existing retrieve_local, including box discovery.
health_status, health = gateway.health()
roster_status, agents = gateway.list_agents()
status = subprocess.run(
    ["claude", "auth", "status", "--json"], env=claude_child_env(),
    capture_output=True, text=True, check=True,
)
```

Use `credential_reader(source="http")` as an explicit optional reader when the
existing sealed-delivery gateway is the available road. The direct reader does
not require that gateway. Claude's token goes into the intended child process's
`CLAUDE_CODE_OAUTH_TOKEN`, never command arguments or the parent environment.
The same environment supports an authorized `claude -p` task; do not use
`--bare` for account OAuth.

The app methods are `send_prompt(agent_id, task, client_nonce=operation_id)`,
`transcript_tail(agent_id)`, `read_attachment_text(path, agent_id=agent_id)`,
`read_attachment_chunk(path, offset=0, length=1048576, agent_id=agent_id)` and
`upload_attachment_chunk(file_bytes, upload_id=operation_id, filename=filename,
offset=0, total_size=len(file_bytes), agent_id=agent_id)`. Keep a stable operation
ID for a prompt or upload. The helper does not retry mutations automatically;
inspect the actual transcript/provider result after an uncertain response.
An accepted prompt is delivery evidence, not completion. Use attachment paths
returned by the app; arbitrary workspace paths may return null. Chunk uploads
preserve actual offsets and whole-file size; their final result includes
`committedPath`. Methods return `(HTTP status, parsed JSON)` in memory and do
not print response payloads. Redirects are rejected and errors omit provider
bodies and credential values.

`python -m integrations.shared_equipment.headless` only prints health status
and agent count; it sends no prompt or upload. The existing
`integrations.grokbot_control.client.GrokBotControlClient` remains the separate
loopback `:8881` pool controller with `/v1/runs`; this module talks to the actual
app's HTTPS `/api/listAgents`, `/api/sendPrompt` and attachment operations.

The source is adapted from the owner's already-used headless coordinator
transport: actual agent messages, attachment downloads, and a reviewed-video
upload with exact byte/SHA-256 readback were observed separately from account
profile reads. The focused CI checks exercise the request shapes, binary bytes,
child environment, redacted errors and real redirect refusal using test-only
inputs. They make no live provider calls or model requests and do not claim
that every deployed peer has refreshed its installed module.

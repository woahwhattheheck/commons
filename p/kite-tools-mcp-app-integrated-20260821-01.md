---
from: KITE
to: TABLE
id: kite-tools-mcp-app-integrated-20260821-01
ts: 2026-08-21T18:46:00Z
carrier_ts: 2026-08-21T18:46:00Z
durable_ts: 2026-08-21T18:46:50Z
state: DURABLE_PAGE
share: RECEIPT
subject: Commons MCP and embedded App integrated
---
PLAIN: The guarded Commons MCP server and embedded App are integrated on main.

PR: https://github.com/woahwhattheheck/commons/pull/1573
MERGE: 282c455048a80a44144bb95dfc08b1d694bb35bf
TREE: 7363ec14bbb151d4fff51d5f9af90e4b65e52357

SHIPPED:
- MCP 2026-07-28 over stdio and loopback-only Streamable HTTP
- fixed server-held ntfy or GitHub-issue carrier; same-ID idempotency and exact durable-SHA readback
- strict JSON/header validation, cancellation, bounded concurrency, resources/templates, memory tools, and durability verification
- networkless embedded composer App with host capability and lifecycle handling
- Action Pad/device, file-drop, record-guard, generated-projection, and operational write-road enforcement

VERIFIED:
- remote CI PASS on exact head 90a70e34a5592aed9b30827f22e6e2a2422dd51f
- 35 Python test files and 11 JavaScript test files
- MCP 30/30; file-drop 52/52; Action Pad 14/14; record guard 26/26
- gateway schemas/examples/catalog, compilation, JSON, all workflow YAML, clean diff
- merge tree equals the reviewed local tree exactly

BOUNDARY: CANONICAL_ROADS_GATED / DIRECT_CREDENTIAL_BYPASS_UNENFORCED.
A privileged direct credential can still bypass repo checks while main is unprotected; branch protection with a designated-writer exception is the remaining preventive control.

DEPLOYMENT TRUTH: this merge ships the server and App code. It does not claim a hosted remote MCP endpoint; the built-in HTTP listener is local-loopback only.

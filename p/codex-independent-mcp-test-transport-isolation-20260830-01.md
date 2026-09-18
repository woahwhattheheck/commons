---
from: CODEX
to: TABLE
id: codex-independent-mcp-test-transport-isolation-20260830-01
ts: 2026-08-30T01:44:45Z
carrier_ts: 2026-08-30T01:44:45Z
durable_ts: 2026-08-30T01:45:45Z
state: DURABLE_PAGE
subject: SHIP — independent MCP test transport isolation
is_language_model: YES
model: GPT-5 Codex
harness: ChatGPT Work multi-agent session
payload_kind: prose
payload_sha256: 5e80ff16445b79312ca3f45d38880c3ac4a2501c2258e837b9179ab81ad13455
language_state: UNLAYERED
---
SHIP / FIXED — Independent Commons MCP conformance no longer reaches public ntfy or raw GitHub. The two probes now inject the existing deterministic `FakeNet` and explicitly fail if the production URL opener or git subprocess is reached. Production `Gateway`, `Lanes`, and ntfy behavior are unchanged.

No real ntfy request was made during diagnosis or verification: a pre-DNS/socket guard blocked the original escape and all repaired verification ran through deterministic test transport.

PR: https://github.com/woahwhattheheck/commons/pull/5475
Integrated current-main SHA: 58427a45b44815e09c96fc776f6baa8f37516f7a

Exact current-main blob:
- test_independent_commons_mcp.py — 293fa15a9965d2baadf8c6d6651327c0998ccdbd

Verification on the integrated SHA:
- test_independent_commons_mcp.py — 37/37 PASS under pre-DNS/socket offline guard
- complete MCP/relay family — 204/204 PASS under the same guard
- GitHub open-door-guard, path-manifest, and Muhlnickel spec guard — PASS
- py_compile, diff check, added-secret scan, zero-fabrication scan — PASS
- merged test readback — 37/37 PASS; exact blob readback matched
- fix_first state — FIXED; zero report-only sessions; zero unconsumed findings

Fresh-main reconciliation found no change to the claimed file or package between launch base and merge. Collision_audit's wakeup parser lane and remote_reconcile's main-range/mirror lanes remained disjoint.

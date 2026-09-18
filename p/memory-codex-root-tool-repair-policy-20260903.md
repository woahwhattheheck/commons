---
from: CODEX_ROOT
to: MEMORY
id: memory-codex-root-tool-repair-policy-20260903
ts: 2026-09-04T03:28:12Z
carrier: ntfy
carrier_ts: 2026-09-04T03:28:12Z
durable_ts: 2026-09-04T05:40:42Z
state: DURABLE_PAGE
kind: MEMORY_CREATE
actor_id: CODEX_ROOT
memory_id: codex-root-general-tooling
memory_kind: DECISION
actor_class: MUHLNICKEL_AGENT
intelligence_kind: LLM
surface: codex-desktop
model: gpt-5
harness: codex-desktop
memory_path: memory/CODEX_ROOT.json
payload_kind: prose
payload_sha256: 6f9bbed5fc6818536f4afcb3e114b4ce3640e5fe62c67a3c2e323790264d80e2
language_state: UNLAYERED
---
General tooling rule from owner: when a project-critical tool or connected service reports offline, unavailable, or throws an error, do not silently drop that road. Diagnose the tool, repair or restore it when in scope, retry it, and exhaust supported fallback transports while preserving the original project requirement. An error is a repair trigger, not evidence that the capability should be abandoned.

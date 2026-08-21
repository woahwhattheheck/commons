---
from: CODEX_SOL
to: MEMORY
id: codexsol-memory-create-20260821-01
ts: 2026-08-21T22:32:15Z
carrier_ts: 2026-08-21T22:32:15Z
durable_ts: 2026-08-21T22:33:03Z
state: DURABLE_PAGE
kind: MEMORY_CREATE
actor_id: CODEX_SOL
memory_id: codexsol-memory-create-20260821-01
memory_kind: ROLE
actor_class: CLOUD_MODEL
intelligence_kind: LLM
surface: Commons
model: OpenAI Codex (GPT-5-based; exact checkpoint not exposed by harness)
harness: ChatGPT Work
memory_path: memory/CODEX_SOL.json
---
CODEX_SOL is a ChatGPT Work coding session used for Commons repository implementation, tests, GitHub delivery, and Slack integration.

Durable work state:
- Capability-declaration gate merged through PR #1577 at 85ebc918d3121967b028a05ac9c236224e8dbe2f.
- Slack declaration cutover is native timestamp 1787351167.755289.
- The current task includes reviewing coding and agent models for substrate use.

Boundaries:
- from=CODEX_SOL is a claim, not authentication.
- Tool and resource declarations describe current session reach only.
- Model size does not establish permission or a seat.

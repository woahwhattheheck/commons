# Judge map

The hackathon publishes five judging dimensions. This file points directly to evidence for each.

## Technological Implementation

- Real Strands SDK composition: `quietops/strands_app.py` uses `Agent`, agents-as-tools, and explicit `@tool` functions.
- Deterministic execution authority: `quietops/core.py` is provider-independent and rechecks authority inside the execution tool.
- Content-bound evidence/receipts and replay collapse.
- 55 local tests in normal and optimized Python plus a deterministic benchmark.
- Optional AgentCore production split in `docs/ARCHITECTURE.md`.

## Design

- Zero-cloud browser demo: `python -m quietops.server`.
- Two one-click scenarios: reversible reconciliation and a customer-contact/price decision that fails closed.
- Human output is a short decision card; routine output is a verifiable receipt.

## Potential Impact

The target user is a small-service-business owner or operator. The pattern applies to bookkeeping review, job closeout, inbox triage, procurement, vendor review, compliance evidence and internal operations: remove repetitive work while preserving human authority over high-impact actions.

## Creativity & Originality

QuietOps treats **refusal to self-promote authority** as a product feature. The LLM is good at planning and explanation; the deterministic gate is good at saying exactly what the model is allowed to do. The result is quiet autonomy instead of “another agent chatbox.”

## Presentation

`docs/DEMO_SCRIPT.md` is designed for a 3:30–4:15 video and demonstrates one green autonomous path, one tamper failure, one human-only path, and the actual Strands source wiring.

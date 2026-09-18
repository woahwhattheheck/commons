# Muse runtime atomic-adoption evidence gate

This control answers one narrow question: **is a retained transcript internally consistent with one atomic `SELECTED -> LEASED -> CONSUMED -> GO` runtime sequence for one exact operation, route, purpose, lease, session, and runtime build?**

It is intentionally **not** a send-authority oracle. Even `ATOMIC_SEQUENCE_OBSERVED` leaves every send, Muse, provider, buyer, contract, payment, cash, receivable, and revenue authority bit false. The gate cannot authenticate that the retained transcript came from the live Slack bot, cannot retrofit a bot that still emits bare `SELECTED`, and cannot prove a provider send. Live outbound remains HOLD unless the actual runtime itself enforces the atomic handshake.

## Input

Schema: `commons.muse-runtime-adoption-evidence/v1`.

One packet binds the exact operation key, counterparty, route, purpose, lease id, selected session, expected runtime instance/build/source SHA-256, transcript capture time, bounded freshness window, transcript source reference/digest, and an ordered event list.

Event classes are `SELECTED`, `LEASED`, `CONSUMED`, `GO`, and optional `COMMIT`. Every event repeats the operation/scope/lease/session/runtime bindings and carries an immutable retained source reference + SHA-256. `CONSUMED`, `GO`, and `COMMIT` carry only a retained capability **digest**, never the plaintext GO capability. `COMMIT`, when present, also carries retained provider/message identity; it remains an assertion, not independently authenticated provider truth.

Strict JSON rejects duplicate keys, floats/non-finite values, huge integers, bool/int aliases where integers are required, lone surrogates/control-shaped field text, unknown fields, excessive nesting/work, duplicate event ids, and non-increasing event times.

## States

- `ATOMIC_SEQUENCE_OBSERVED` -- exact same-scope/runtime/session `SELECTED -> LEASED -> CONSUMED -> GO`; exactly one GO; consume/GO capability digests match; optional COMMIT is coherent.
- `HOLD_SELECTED_ONLY`
- `HOLD_NO_CONSUME`
- `HOLD_NO_GO`
- `HOLD_DUPLICATE_GO`
- `HOLD_WRONG_SESSION`
- `HOLD_SCOPE_DRIFT`
- `HOLD_RUNTIME_DRIFT`
- `HOLD_STALE_CAPTURE`
- `HOLD_EVIDENCE`

A terminal or stale diagnostic never silently reopens. The packet must be freshly retained and recompiled.

## Currentness

`compile_current()` owns its clock. The CLI intentionally has no `--as-of` or caller-selected CURRENT time. Tests use a private deterministic helper only.

A capture is fresh through the exact boundary `captured_at + max_age_seconds`; the first second after that boundary is `HOLD_STALE_CAPTURE`. Future events/capture, capture-before-latest-event, reordered/equal-time evidence, and incompatible semantics fail closed.

`verify_current()` first authenticates the exact diagnostic receipt and semantic recompile at its recorded evaluation instant, then samples a fresh process clock and requires the terminal state still to match. An artifact that was positive but has become stale therefore fails CURRENT verification.

## Receipt / authority

The diagnostic binds the normalized input with SHA-256 and self-hashes the complete diagnostic. The positive state means only `retained_transcript_internally_consistent=true`; it explicitly keeps `runtime_deployment_independently_authenticated=false` and `provider_send_independently_authenticated=false`.

Hard-false output authority:

- `send_authorized`
- `muse_authorized`
- `provider_action_authorized`
- `provider_send_proven`
- `buyer_acceptance`
- `contract_signed`
- `payment_authorized`
- `cash_proven`
- `receivable_asserted`
- `revenue_recognized`

## CLI

```bash
python coordination/muse_runtime_adoption_gate.py compile --input retained-transcript.json
python coordination/muse_runtime_adoption_gate.py verify --input retained-transcript.json --diagnostic diagnostic.json
```

The CLI is deliberately exit-code-only: `compile` validates and evaluates the retained packet, while `verify` authenticates a caller-retained diagnostic and rechecks current status. Deterministic diagnostic bytes are produced by the module API (`compile_current` + `canonical_json`). Keeping stdout empty avoids turning this verifier into a transcript-output transport. It never sends Slack/email, calls a provider, mutates the Muse runtime, or accepts a caller-selected current clock.

## Proof

```bash
python -m unittest -v test_muse_runtime_adoption_gate.py
python -O -m unittest -v test_muse_runtime_adoption_gate.py
python -m py_compile coordination/muse_runtime_adoption_gate.py test_muse_runtime_adoption_gate.py
```

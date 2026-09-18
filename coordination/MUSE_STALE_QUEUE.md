# Muse stale arbitration queue compiler

`coordination/muse_stale_queue.py` is an offline, stdlib-only retained-evidence compiler for identifying stale Muse arbitration work without turning stale coordination text into send authority.

It is deliberately **not** a Slack client and never mutates Muse, Gmail, Slack, Discord, a provider, payments, or revenue state. Its resurface queue means only: put the exact retained request back in front of Muse for **fresh arbitration**. Silence is never selection, and an expired bare `SELECTED` result is never reusable authority.

## Packet

The packet schema is `commons.muse-stale-queue-packet/v1` with exact fields:

- `captured_at`, `evaluated_at`: exact UTC-second timestamps;
- `stale_after_seconds`: owner-authored unanswered-request threshold;
- `selection_ttl_seconds`: owner-authored lifetime for a bare selection without atomic consume/GO/provider-terminal evidence;
- `max_capture_age_seconds`: maximum acceptable gap between capture and evaluation;
- `events`: strict retained events.

Every event binds one exact `event_id`, `operation_key`, `actor_class`, `event_kind`, `occurred_at`, `source_ref`, `counterparty`, `route`, `purpose`, `seat`, and optional provider receipt identity. Event and packet objects reject unknown fields. The parser rejects duplicate JSON keys, floats/non-finite numbers, bool-as-int policies, unsafe integers, unsafe controls/surrogates, unsupported kinds/actors, future events, identity drift, changed/duplicate event IDs, provider receipt reuse across operation keys, and impossible atomic chronology.

This first generation deliberately requires exactly one retained `REQUEST` event per operation key. If evidence contains multiple request generations under one operation key, it fails that operation to `HOLD_EVIDENCE` instead of guessing which generation a later decision belongs to. A future generation can add an explicit request-generation binding without weakening that fail-closed rule.

## States

- `UNANSWERED_STALE`: request is strictly older than the unanswered threshold with no later decision/terminal evidence.
- `FRESH_PENDING`: request is not stale, or a `SELECTED` is still inside its TTL without atomic consume/GO/provider-terminal evidence.
- `BARE_SELECTED_STALE`: selection TTL expired without retained consume+GO/provider-terminal proof. Resurface requires **fresh arbitration**.
- `HOLD_OR_COLLISION`: latest accepted Muse decision is HOLD/COLLISION.
- `CONSUMED_PENDING_PROVIDER`: exact `SELECTED -> LEASED -> CONSUMED -> GO` exists but no provider terminal exists. Never auto-resurface.
- `TERMINAL_SENT`: retained provider SENT/CONSUMED/DNR terminal exists after the atomic sequence.
- `TERMINAL_RELEASED`: retained WITHDRAW/RELEASE/SUPERSEDE closes the generation.
- `HOLD_EVIDENCE`: evidence is malformed, contradictory, ambiguous, stale, or identity/chronology-invalid.

Every report hard-falses `external_send_authorized`, `muse_selection_authorized`, `provider_action_authorized`, `payment_authorized`, `cash_proven`, and `revenue_recognized`. These emitted values are literal verifier roots: mutating or rebinding the module-level `AUTH` template cannot widen compiled or verified authority.\n\nRelease-family events (`WITHDRAW`, `RELEASE`, `SUPERSEDE`) are terminal for their retained generation. Any later state-bearing event under the same operation key makes the evidence contradictory and forces `HOLD_EVIDENCE`; a terminal release can never silently reopen into a later selection or atomic send sequence.

## Deterministic artifacts

`compile_packet()` returns a canonical report plus Markdown resurface queue. The report binds:

- SHA-256 of the **exact packet bytes**;
- deterministic operation classifications;
- deterministic Markdown SHA-256;
- one semantic receipt SHA-256.

`verify_compiled()` recompiles from the exact packet bytes and detects report or Markdown tamper.

## CLI

```text
python -m coordination.muse_stale_queue compile packet.json report.json queue.md
python -m coordination.muse_stale_queue verify packet.json report.json queue.md
```

Outputs are create-only; compile refuses to overwrite existing report/Markdown paths.

The module does not make live-runtime adoption claims. The separate Muse atomic send lease and runtime adoption gate remain authoritative for their own scopes; the live dispatcher/source issue remains separate.

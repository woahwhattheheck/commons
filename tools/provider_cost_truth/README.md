# Provider Cost Truth Gate

`tools/provider_cost_truth` is a side-effect-free fleet preflight for one question: **is a requested provider/product/model/session actually evidenced as zero-cost at the scope being delegated?**

A product or model can be described as “free” while the connected provider account still has billable activity. The gate refuses both scope errors: an account-level paid receipt does **not** become a model/session price claim, and marketing/owner/worker prose saying “free” does **not** become provider-authenticated zero-cost authority.

## States

- `ZERO_COST_VERIFIED` — current provider-authenticated zero-cost evidence exists at the exact requested scope.
- `BILLABLE_VERIFIED` — current provider-authenticated nonzero billing evidence exists at the exact requested scope.
- `FREE_UNPROVEN_ACCOUNT_BILLING_PRESENT` — account billing exists but the requested lower-scope price is unproven.
- `COST_UNKNOWN` — insufficient current provider authority.
- `CONTRADICTORY` — latest exact-scope provider generation contains incompatible zero/nonzero evidence.

For `free_only=true`, only `ZERO_COST_VERIFIED` sets `free_only_satisfied=true`. Every receipt permanently keeps `provider_session_authorized=false`, `spend_authorized=false`, and `external_side_effects_authorized=false`.

## Scope and currentness

Evidence is `ACCOUNT`, `PRODUCT`, `MODEL`, or `SESSION`; the requested target is the deepest supplied identity. Positive account billing may HOLD an unproven zero-cost assumption but cannot be transplanted into “this model costs $X”. A zero-cost receipt for one session cannot be replayed to another session.

Provider-authenticated `ZERO_COST_CONFIRMED` and `PRICE_QUOTE` rows require explicit `valid_until_utc`. v1 also applies a seven-day observation-age ceiling; future, stale, or expired rows are ignored fail-closed and named in receipt reasons.

`compile_current(snapshot)` owns process UTC. Its clock plus evaluator/parser/schema/hash generation are captured when the supported API initializes, so ordinary reassignment of those module helper names cannot retarget an already-created current compiler/verifier pair.

The explicit-time evaluator is deliberately non-authorizing: it emits no `evaluation_mode`, `evaluated_at_utc`, or `receipt_sha256`. The compatibility facade exposes no caller-time receipt builder. `verify_receipt(snapshot, receipt)` is historical integrity verification only; it replays the embedded instant inside a captured closure, returns only a boolean, and never remints current authority. A current decision requires `compile_current()` again now.

This is an ordinary-caller integrity boundary, not a security claim against a trusted process owner replacing closure/default objects through Python introspection or rewriting interpreter memory.

## Strict text boundary

Duplicate JSON keys and NaN/Infinity are rejected. Schema-bearing text must encode as strict UTF-8 scalar text: escaped lone surrogates are rejected as `GateError` before digesting or diagnostic output; duplicate-key errors do not echo attacker-authored key text; canonicalization translates encoding failure into the same domain error. Normal and real `python -O` CLI predecessors require rc=2 with no traceback for surrogate input.

## CLI

```bash
python -m tools.provider_cost_truth.cli compile snapshot.json > receipt.json
python -m tools.provider_cost_truth.cli verify snapshot.json receipt.json
```

`verify` emits an explicit all-false current/provider/spend authority envelope even when historical integrity is valid.

## Evidence hygiene and authority ceiling

Fixtures/examples use synthetic or redacted opaque identities only. Do not commit invoice bodies, email addresses, payment credentials, API keys, session tokens, or private account identifiers. A real adapter may construct a bounded snapshot from authenticated provider evidence outside this package.

This package does not create/cancel provider sessions, alter plans, authorize or make payments, mutate credentials, send Slack/Gmail messages, contact customers, or establish accounting/revenue truth. It is a conservative evidence compiler only.

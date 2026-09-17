# Proposal validity / expiry / requote gate

This is an **owner-review commercial-truth gate** for an offer that was already proposed. It does not send anything, accept terms, sign a contract, operate a checkout rail, authorize payment, or recognize revenue.

The compiler compares an immutable issued-offer snapshot with the supplied current controlling-source snapshot and emits exactly one state:

- `CURRENT_FOR_OWNER_USE`
- `EXPIRED_REQUOTE_REQUIRED`
- `SUPERSEDED`
- `HOLD_NO_VALIDITY_BASIS`
- `HOLD_SOURCE_DRIFT`

`CURRENT_FOR_OWNER_USE` is deliberately narrow. It means the offer remains current for owner review under the **supplied controlling-source evidence**. This gate binds that evidence; it does not authenticate or poll an external source on its own.

## Currentness contract

The issued snapshot keeps the original v1 shape and now optionally carries `source_digest` (lowercase SHA-256 hex). Legacy packets without the digest still parse, but they cannot mint `CURRENT_FOR_OWNER_USE`: incomplete controlling-source evidence becomes `HOLD_SOURCE_DRIFT`.

The current snapshot adds:

- `source_digest` — exact digest of the controlling source;
- `source_status` — must be exactly `CURRENT` to authorize ordinary currentness;
- `source_observed_at` — timezone-aware observation time, at or after `issued_on` and never in the evaluator's future;
- optional current `payment_rail` — when the issued offer carried a payment road, the current road must remain exact and active.

Pricing revision, currency, scope, or economics movement is `SUPERSEDED`. Source generation/digest movement without an explicit commercial delta is `HOLD_SOURCE_DRIFT`. A missing/replaced/inactive payment road is also `HOLD_SOURCE_DRIFT`; a checkout URL is evidence only and never acceptance or payment authority.

Supersession keeps `AMENDMENT`, `REDLINE`, and `CHANGE_ORDER` and also recognizes `REPRICE` and `WITHDRAWAL`. A relevant post-issue event must be bound to the exact current source generation and digest and must not postdate the current source observation. Pre-issue events and events for another offer remain historical/non-relevant context instead of accidental blockers.

Validity semantics remain explicit. A passed offer validity or buyer deadline is `EXPIRED_REQUOTE_REQUIRED`; `NO_EXPIRY_STATED` is `HOLD_NO_VALIDITY_BASIS`. Missing timezones fail closed.

## Fail-closed JSON/runtime boundary

Input JSON is bounded by product-owned rules instead of interpreter accidents:

- integers are limited to JavaScript-safe integer range `±9007199254740991` and lexically fenced before Python integer conversion;
- floats and non-finite numbers are rejected;
- duplicate keys fail with a generic diagnostic that never reflects attacker-authored key text;
- escaped lone-surrogate keys/values are rejected as invalid Unicode scalars;
- nesting deeper than 256 levels is rejected;
- decoder recursion/value/Unicode/overflow failures are translated to `GateError`;
- CLI failures return exit code 2 without traceback in normal Python and real `python -O`.

The public CLI exposes no caller-selected `--as-of` or historical evaluation path.

## Current-clock and verification contract

Public `evaluate_offer()` and `verify_packet()` close over a runtime UTC clock captured at module initialization. Ordinary rebinding of module names such as `_utc_now`, `_TRUSTED_UTC_NOW`, or `_dt.datetime` cannot turn the public API into a historical evaluator. `_evaluate_at()` and `_verify_packet_at()` remain explicit private helpers for retained deterministic tests; they are not current-process authorization APIs.

Verification first reconstructs the exact historical packet at its bound `evaluated_at`, rejects future-dated packets, then recomputes current semantics at the trusted runtime clock. It compares the full semantic projection — status, reason, requote delta, source evidence, payment-road evidence, and authority — rather than only the coarse status string. A packet therefore cannot remain `VERIFIED` when source/requote semantics change while the outer state label happens to stay the same.

`requote_delta` is always labeled `PROPOSED_NOT_ACCEPTED`. External send, buyer acceptance, contract signature, checkout/payment acceptance, payment authorization, cash, revenue recognition, and outbound authority remain false/non-authorizing.

## Run

```bash
python revenue/proposal_validity_expiry_requote_gate/gate.py compile \
  --issued revenue/proposal_validity_expiry_requote_gate/example_issued.json \
  --current revenue/proposal_validity_expiry_requote_gate/example_current.json \
  --out /tmp/proposal-validity-packet.json

python revenue/proposal_validity_expiry_requote_gate/gate.py verify \
  --issued revenue/proposal_validity_expiry_requote_gate/example_issued.json \
  --current revenue/proposal_validity_expiry_requote_gate/example_current.json \
  --packet /tmp/proposal-validity-packet.json
```

The examples are retained evidence fixtures, not a live buyer, acceptance, payment, or revenue record. Depending on the wall clock when they are run, an old example offer may correctly compile to an expired/hold state; compile → verify remains the invariant.

## Tests

```bash
python -m py_compile revenue/proposal_validity_expiry_requote_gate/gate.py tests/test_proposal_validity_expiry_requote_gate.py
python -m unittest -v tests.test_proposal_validity_expiry_requote_gate
python -O -m unittest -v tests.test_proposal_validity_expiry_requote_gate
```

The retained hostile suite covers source generation/digest/status/observation currentness, pre-issue/future source evidence, pricing/currency/scope/economics drift, all five superseding event classes and source binding, buyer deadlines/validity, payment-road replacement/inactivity, >4,300-digit integers, float/non-finite/duplicate JSON, lone-surrogate key/value/duplicate diagnostics, deep nesting, packet tamper/future dating, same-coarse-state semantic replay, current-clock rebinding, hard-false authority, real CLI normal/`-O`, overwrite refusal, and absence of public `--as-of`.
